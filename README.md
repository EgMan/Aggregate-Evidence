# AggregateEvidence
Tool for aggregating multiple .xml encoded junit evidence files into a single file.

The script automatically identifies an evidence file which consists of a superset of all the test cases.  Its test failures are then compared against the other evidence files, and if they pass anywhere else, those test cases are stiched in.  Meta-data like test run attributes are also updated accordingly.  

Partial runs and runs that have been quit prematurely are handled.  The only requirement is that at least one full run is provided to act as a superset.  

## Prerequisites
Installation of [Python](https://www.python.org/downloads/) (either 2 or 3) is required.

## Usage
Export all evidence into its own directory.  Remember to include at least one full run which contains all of the test cases put into that directory.  

The script accepts a single argument: a path to the directory with your evidence.  

After executing, the aggregated evidence file will have been written to a subdirectory "aggregated" created within your evidence directory.

## Example
```
python aggregateEvidence.py ./path/to/evidence/directory
```

## Support
Python 2, 3
Junit 3 and 4 have been tested.  Junit 5 should work too probably.
