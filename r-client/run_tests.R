
# Define a function to check testthat results.
CheckTestThatResults <- function(testthat_results){
    
    outcomes <- unlist(lapply(testthat_results
                              , function(x){lapply(x$results, function(y){class(y)[1]})}))
    
    numErrors <- sum(outcomes %in% c('expectation_failure','expectation_error'))
    numWarnings <- sum(outcomes == 'expectation_warning')
    numPassed <- sum(outcomes == 'expectation_success')
    
    # generate and trim outcomes table for display
    outcomesTable <- data.table::as.data.table(testthat_results)
    outcomesTable[, file := strtrim(outcomesTable[, file], 17)]
    outcomesTable[, test := strtrim(outcomesTable[, test], 48)]
    data.table::setnames(outcomesTable, old = 'real', new = 'testTime')
    
    print("The Test Results are:")
    print(paste('Num Errors:', numErrors))
    print(paste('Num Warnings:', numWarnings))
    print(paste('Num Passed:', numPassed))
    print("")
    
    return(numErrors == 0)
}

# Run our unit tests, return with a non-zero exit code if any failed
testStatus <- CheckTestThatResults(devtools::test())
if (!testStatus) {
    print('Tests have failed!')
    q(status = 1, save = 'no')
}
