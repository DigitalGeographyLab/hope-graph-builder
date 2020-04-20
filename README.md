# hope-graph-tools

This repository contains utilities for importing and processing street network graphs exported from OpenTripPlanner. The graphs will be used at least by [hope-green-path-server](https://github.com/DigitalGeographyLab/hope-green-path-server). 

## Features
* Import graph data to igraph from [CSV files exported by OTP](https://github.com/DigitalGeographyLab/OpenTripPlanner/pull/1)<sup>[1](src/otp2igraph_import/otp2igraph_import.py)</sup>
* Remove private, unwalkable and street segments not suitable for biking from a graph<sup>[1](src/otp2igraph_import/otp2igraph_import.py)</sup>
* Decompose graph and remove unconnected edges & nodes<sup>[1](src/otp2igraph_import/otp2igraph_import.py)</sup>
* Create a subset of the graph for Helsinki Metropolitan Area<sup>[1](src/otp2igraph_import/otp2igraph_import.py)</sup>
* Export raw and processed graph features to GeoPackages for debugging<sup>[1](src/otp2igraph_import/otp2igraph_import.py)</sup>
* Set up a custom [schema](src/common/schema.py) for graph features
* Export graph to GraphML format<sup>[2](src/common/igraph.py)</sup>
* _TODO: Join environmental noise data to graph features to enable exposure-based routing_

## Tech
* Python 3.6
* igraph
* Shapely
* GeoPandas

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
$ python otp2igraph_import_test.py
```
