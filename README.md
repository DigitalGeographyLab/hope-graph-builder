# hope-graph-builder

This repository contains utilities for importing and processing [OpenStreetMap](https://www.openstreetmap.org/copyright) based street network graphs exported from OpenTripPlanner. The graphs will be used at least in [hope-green-path-server](https://github.com/DigitalGeographyLab/hope-green-path-server) which is a route planner for walking and cycling that suggests routes with less traffic noise and air pollution. 

## Features
* [otp_graph_import.py](src/otp_graph_import/otp_graph_import.py)
    * Import graph data to igraph from [CSV files exported by OTP](https://github.com/DigitalGeographyLab/OpenTripPlanner/pull/1)
    * Remove private, unwalkable and street segments not suitable for biking from a graph
    * Decompose graph and remove unconnected edges & nodes
    * Create a subset of the graph for Helsinki Metropolitan Area
    * Export raw and processed graph features to GeoPackages for debugging
* [noise_data_preprocessing.py](src/noise_data_preprocessing/noise_data_preprocessing.py)
    * Preprocess noise data from different sources to common schema
* [noise_graph_join.py](src/noise_graph_join/noise_graph_join.py)
    * Join environmental noise data to graph features to enable exposure-based routing
    * Interpolate noise values for edges missing them

## Tech
* Python 3.6
* igraph
* GeoPandas
* Shapely

## Installation
```
$ git clone git@github.com:DigitalGeographyLab/hope-graph-tools.git
$ cd hope-graph-tools/src
$ conda env create -f env_graph_tools.yml
```

## Running the tests
```
$ conda activate graph-tools
$ cd src/test
$ python otp_graph_import_test.py
$ python noise_graph_join_test.py
```
