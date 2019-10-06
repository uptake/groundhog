
context("\n>> append_slope_features")

# Configure logger (suppress all logs in testing)
loggerOptions <- futile.logger::logger.options()
if (!identical(loggerOptions, list())){
    origLogThreshold <- loggerOptions[[1]][['threshold']]
} else {
    origLogThreshold <- futile.logger::INFO
}
futile.logger::flog.threshold(0)

test_that("append_slope_features should work", {

    # Make a test dataset
    someDT <- data.table::data.table(
        longitude = runif(10, -110, -109)
        , latitude = runif(10, 45, 46)
        , dateTime = seq.POSIXt(from = as.POSIXct("2017-01-01 00:00:00")
                                , to = as.POSIXct("2017-01-15 00:00:00")
                                , length.out = 10)
        , assetId = c(rep("ABC", 5), rep("DEF", 5))
    )

    # Append features
    groundhog::append_slope_features(someDT
                                   , hostName = "localhost"
                                   , port = 5005)

    expect_true(data.table::is.data.table(someDT))
    expect_true(nrow(someDT) == 10)
    expect_named(someDT
                 , c("longitude", "latitude", "dateTime", "assetId", "bearing", "slope", "elevation")
                 , ignore.order = TRUE
                 , ignore.case = FALSE)
    expect_true("POSIXct" %in% class(someDT[, dateTime]))
    expect_true(is.numeric(someDT[, bearing]))
    expect_true(is.numeric(someDT[, slope]))
    expect_true(is.numeric(someDT[, elevation]))
})
