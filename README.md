# European COVID19-forecast Hub Validations

This repository contains the source code for the validation checks that are run on every pull request to the [covid19-forecast-hub-europe](https://github.com/epiforecasts/covid19-forecast-hub-europe) repository to ensure a consistent forecast [format](https://github.com/epiforecasts/covid19-forecast-hub-europe/wiki/Forecast-format). 

#### Working with the main hub repository

This repository is a submodule of the main forecast hub repository, as `covid19-forecast-hub-europe/validation`. 

Clone both repositories together using:
```
git clone covid19-forecast-hub-europe --recurse-submodules
```

If you already have an existing clone of the main hub repository, add or pull changes to this submodule with:
```
git submodule update --init --recursive
```
