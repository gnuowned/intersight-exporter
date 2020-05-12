#Intersight-Exporter is an Prometheus Metrics Exporter for Cisco Intersight

##Installation
#Requirements

Python3.7
pip3

#Running Locally

Install Prometheus client_python
```
pip install prometheus_client
```
Install intersight Python
```
pip install git+https://github.com/CiscoUcs/intersight-python
```
Clone this repo:
```
git clone https://github.com/gnuowned/intersight-exporter
```

Login Intersight.com then Settings > API Keys > Generate API Key

Add your Intersight Keys and Api Key ID to intersight_api_params.json
```
cd intersight-exporter
mv example_intersight_api_params.json intersight_api_params.json
vi intersight_api_params.json
```

Run intersight-exporter
```
python intersight_exporter.py
```

#WIP Help Wanted


