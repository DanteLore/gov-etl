resource "aws_glue_catalog_table" "nomis_census_car_availability" {
  name          = "nomis_census_car_availability"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "Census 2021 TS045 car or van availability per household, England and Wales by output area, LSOA, MSOA, local authority and ward"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/nomis_census_car_availability/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "geography_code"
      type = "string"
    }
    columns {
      name = "geography_name"
      type = "string"
    }
    columns {
      name = "total_households"
      type = "int"
    }
    columns {
      name = "no_car"
      type = "int"
    }
    columns {
      name = "one_car"
      type = "int"
    }
    columns {
      name = "two_cars"
      type = "int"
    }
    columns {
      name = "three_or_more_cars"
      type = "int"
    }
  }

  partition_keys {
    name = "geography_level"
    type = "string"
  }
}
