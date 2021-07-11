# hope-graph-builder (deprecated)

This repository is deprecated as a separate project - all functionality have been integrated into [hope-green-path-server](https://github.com/DigitalGeographyLab/hope-green-path-server). 

This repository contains utilities for importing and processing [OpenStreetMap](https://www.openstreetmap.org/copyright) based street network graphs [created and exported with OpenTripPlanner](https://github.com/DigitalGeographyLab/OpenTripPlanner/pull/1). The graphs will be used at least in [hope-green-path-server](https://github.com/DigitalGeographyLab/hope-green-path-server) which is a route planner for walking and cycling that finds routes with less traffic noise and air pollution. 

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
    * Join environmental noise data to graph features to enable noise exposure based routing
    * Interpolate noise values for edges missing them (on municipal boundaries)
* [green_view_join_v1.py](src/green_view_join_v1/green_view_join_v1.py)
    * Join street level Green View Index (GVI) values from GVI point data and land cover layers
* [graph_export.py](src/graph_export/graph_export.py)
    * Calculate biking impedances ("adjusted lengths") by bike safety factors
    * Finalize graph for Green Paths route planner by exporting only relevant attributes

## Materials
* [SYKE - Traffic noise modelling data from Helsinki urban region](https://www.syke.fi/en-US/Open_information/Spatial_datasets/Downloadable_spatial_dataset#E)
* [Traffic noise zones in Helsinki 2017](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-meluselvitys-2017)
* [OpenStreetMap](https://www.openstreetmap.org/about/)
* [Green View Index (GVI) point data](https://doi.org/10.1016/j.dib.2020.105601)
* [Land cover data](https://hri.fi/data/fi/dataset/paakaupunkiseudun-maanpeiteaineisto)

## Tech
* Python 3.8
* igraph
* GeoPandas
* Shapely

## Installation
```
$ git clone git@github.com:DigitalGeographyLab/hope-graph-builder.git
$ cd hope-graph-builder/src
$ conda env create -f env_graph_tools.yml
```

## Running the tests
```
$ conda activate graph-tools
$ cd src/test
$ python -m pytest green_view_join_v1_test.py -v
$ python otp_graph_import_test.py
$ python noise_graph_join_test.py
```
