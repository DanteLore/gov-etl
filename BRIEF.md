
Brief for creating a suite of ETLs to pull various UK government datasets into my own personal datalake, hosted in AWS S3.

# Useful links:
* My personal coding preferences:  https://dantelore.com/AI.md
* Blog posts about the data lake and pipeline structure:  https://dantelore.com/posts/simplest-data-pipeline/
* How the data will be used (outside the scope of this project phase): https://dantelore.com/posts/simplest-data-model/

# Reference project
You can use the project in "C:/Development/energy-etl" as an example of the architecture we are going to use.  We want to stay consistent with this architecture - creating glue table definitions (terraform), lambda function to periodic data fetching and backfill script to run locally.  Where this pattern doesn't fit (e.g. datasets only made available annually or in odd formats) ask me! 

Read "C:/Development/energy-etl/README.md" and "C:/Development/energy-etl/STRUCTURE.md" for more info.

For now we are interested in LOADING the data only.  Getting to a point where we have the data in S3 with glue tables queryable with Athena in the 'dantelore.data.incoming' bucket.  Adding modelling in 'dantelore.data.lake' is future work and out of scope now.

# First job:  Get set up

Create the terraform files, python venv, requirements.txt, README docs, folder structure etc.  Then work on the data sources in order:

# Datasets we're going to pull

We'll have to research the specific data feeds we need.  There are three main areas we're interested in at this stage, which we can address in order.

## 1. UK road traffic census data

We are interested in collecting all the data we can on road usage.  "DfT AADF data" was suggested.

We're looking to get a recent, high quality and high granularity data on traffic levels across the UK so we can look at trends in traffic levels over time etc.

We are not interested in any data from outside the UK.

## 2. House price data

We are looking to download the gov.uk house price dataset in order to investigate house price trends in the UK over time.  

As supporting data we might also want to download postcode lookups, town/city area data or anything else which helps group house price data into usable clusters and groups.  

## 3. Rail data

We are interested in downloading rail performance data for railways in the UK.  We are interested in service levels, maintenance, punctuality, delays and closures.  We want to get a full picture of the UK rail system - how it is used and is changing over time, which lines perform better/worse and so on.
