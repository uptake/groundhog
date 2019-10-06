#' @title Slope and Elevation Features
#' @name append_slope_features
#' @description This function takes a \code{\link{data.table}} with GPS coordinates
#'              and enriches it with some elevation and slope features. The function
#'              hits the public Shuttle Radar Topography Mission (SRTM) dataset
#'              to get elevation data for each lat-lon pair in your dataset.
#' @param DT A \code{\link{data.table}} with at least the following columns:
#' \itemize{
#'     \item{\emph{latitude}}{: latitude in degrees}
#'     \item{\emph{longitude}}{: longitude in degrees}
#'     \item{\emph{assetId}}{: identifier for your asset. Requests are separated
#'                           by assetId to avoid computing features like \code{bearing}
#'                           over data from different physical things}
#'     \item{\emph{bearing}}{: (optional). If given, this should be the final bearing
#'                          in degrees. If not supplied, this will be calculated
#'                          from consecutive observations}
#' }
#' @param hostName A string with the host running groundhog. By default, this
#'                 function expects that you're running the app on \code{localhost}.
#' @param port Port that the service is running on. 5005 by default. You PROBABLY
#'             won't ever have to change this.
#' @importFrom assertthat assert_that has_name
#' @importFrom data.table := as.data.table key rbindlist setnames setorderv
#' @importFrom uuid UUIDgenerate
#' @export
#' @return Nothing. This function will modify \code{DT} in place by appending columns
#' @references \href{https://www2.jpl.nasa.gov/srtm/}{Background on SRTM:}
#' @examples
#' \dontrun{
#' library(data.table)
#'
#' # Create a sample dataset
#' someDT <- data.table::data.table(
#'      longitude = runif(10, -110, -109)
#'      , latitude = runif(10, 45, 46)
#'      , dateTime = seq.POSIXt(from = as.POSIXct("2017-01-01", tz = "UTC")
#'                              , to = as.POSIXct("2017-01-15", tz = "UTC")
#'                              , length.out = 10)
#'      , assetId = c(rep("ABC", 5), rep("DEF", 5))
#' )
#'
#' # Append slope fearures
#' groundhog::append_slope_features(someDT, hostName = "localhost", port = 5005)
#' }
append_slope_features <- function(DT
                                , hostName = "localhost"
                                , port = 5005
                                ){

    assertthat::assert_that(
        all(c("dateTime", "assetId", "latitude", "longitude") %in% names(DT))
    )

    # Build a join table on the original DT. We'll ship this "unique_key"
    # with the request and use it to join client-side. Otherwise, joining on
    # lat-lon can fail because of different precision levels
    #
    # Sorting these so we know the results can be appended to DT in place
    joinKeys <- sort(sapply(1:nrow(DT), uuid::UUIDgenerate))

    if ("bearing" %in% names(DT)){
        tempDT <- DT[, .(assetId, dateTime, latitude, longitude, bearing, unique_key = joinKeys)]
    } else {
        tempDT <- DT[, .(assetId, dateTime, latitude, longitude, unique_key = joinKeys)]
    }

    # Grab a JSON payload for each asset in DT
    assets <- tempDT[, unique(assetId)]
    log_info(sprintf("Running groundhog for %s assets", length(assets)))

    # Submit one request per asset
    payloads <- lapply(assets
                       , FUN = function(asset, DT){.GetPayloadJSON(tempDT[assetId == asset])}
                       , DT = tempDT)

    # Submit requests
    assetNumber <- 1
    numAssets <- length(assets)
    responseList <- lapply(payloads
                           , FUN = function(payload, hostName, port){
                               log_info(sprintf("Working on asset %s/%s", assetNumber, numAssets))
                               assetNumber <<- assetNumber + 1
                               .GroundhogQuery(
                                        hostName = hostName
                                        , port = port
                                        , payloadJSON = payload
                                )
                              }
                           , hostName = hostName
                           , port = port)

    # Parse into one data.table
    resultDT <- data.table::rbindlist(
        responseList
        , fill = TRUE
    )

    data.table::setnames(resultDT, old = c("geo_point.lat", "geo_point.lon")
                         , new = c("latitude", "longitude"))

    # Instead of copying the whole DT (which could be yuge), we can do a join on
    # the relevant fields then do in-place assignments....check this out
    joinDT <- merge(
        x = tempDT
        , y = resultDT
        , by = "unique_key"
        , all.x = TRUE
        , sort = FALSE
    )
    data.table::setorderv(joinDT, "unique_key")

    # Hopefully nothing broke
    assertthat::assert_that(nrow(DT) == nrow(joinDT)
                            , is.null(data.table::key(joinDT))
                            , identical(joinDT[, unique_key], tempDT[, unique_key]))

    # Add any cols that we got from the API
    # NOTE: ignoring unique_key and stride
    newCols <- base::setdiff(names(resultDT), c(names(DT), "unique_key", "stride"))
    for (newCol in newCols){
        `__values__` <- joinDT[, get(newCol)]
        log_info(sprintf("Appending %s", newCol))
        DT[, (newCol) := `__values__`]
    }

    log_info("Done appending elevation features")
    return(invisible(NULL))
}


# [name] .GroundhogQuery
# [description] Hit the groundhog API and return the response
#               as a data.table
# [param] hostName A string with the host the app is running on. Assumes port 5000
# [param] payloadJSON A JSON string with the query (set of coords)
#' @importFrom data.table as.data.table
#' @importFrom httr add_headers content RETRY stop_for_status
#' @importFrom jsonlite fromJSON
.GroundhogQuery <- function(hostName, port, payloadJSON){

    response <- httr::RETRY(verb = "POST"
                            , paste0("http://", hostName, ":", port, "/groundhog")
                            , body = payloadJSON
                            , httr::add_headers("Content-Type" = "application/json")
                            , times = 5)
    httr::stop_for_status(response)

    responseDT <- data.table::as.data.table(
        jsonlite::fromJSON(
            # Suppress that annoying message about encodings from httr::content
            suppressMessages({
                httr::content(
                    response,
                    as = "text"
                )
            })
            , flatten = TRUE
        )
    )

    return(responseDT)
}


# [description] Format a request payload form a data.table of signal data
# [param] DT a data.table with your signal data
#' @importFrom data.table setorderv
#' @importFrom jsonlite toJSON
.GetPayloadJSON <- function(DT){

    # TODO: fix this if statement it's gross
    if ("bearing" %in% names(DT)){
        uniqueDT <- unique(
            DT[!is.na(latitude) & !is.na(longitude)
               , .(dateTime, longitude, latitude, bearing, unique_key)]
            , by = c('latitude', 'longitude')
        )
    } else {
        uniqueDT <- unique(
            DT[!is.na(latitude) & !is.na(longitude)
               , .(dateTime, longitude, latitude, unique_key)]
            , by = c('latitude', 'longitude')
        )
    }

    # Order the table in ascending order by date to be sure
    # bearing calcs work correctly
    data.table::setorderv(uniqueDT, c("dateTime"))
    uniqueDT[, dateTime := NULL]

    return(jsonlite::toJSON(uniqueDT))
}
