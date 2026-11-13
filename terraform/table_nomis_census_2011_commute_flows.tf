resource "aws_glue_catalog_table" "nomis_census_2011_commute_flows" {
  name          = "nomis_census_2011_commute_flows"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "Census 2011 WU03EW home to workplace flows by method of travel, MSOA and local authority, England and Wales"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/nomis_census_2011_commute_flows/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "home_code"
      type = "string"
    }
    columns {
      name = "home_name"
      type = "string"
    }
    columns {
      name = "workplace_code"
      type = "string"
    }
    columns {
      name = "workplace_name"
      type = "string"
    }
    columns {
      name = "all_methods"
      type = "int"
    }
    columns {
      name = "work_from_home"
      type = "int"
    }
    columns {
      name = "underground_metro_tram"
      type = "int"
    }
    columns {
      name = "train"
      type = "int"
    }
    columns {
      name = "bus_coach"
      type = "int"
    }
    columns {
      name = "taxi"
      type = "int"
    }
    columns {
      name = "motorcycle"
      type = "int"
    }
    columns {
      name = "car_driver"
      type = "int"
    }
    columns {
      name = "car_passenger"
      type = "int"
    }
    columns {
      name = "bicycle"
      type = "int"
    }
    columns {
      name = "on_foot"
      type = "int"
    }
    columns {
      name = "other"
      type = "int"
    }
  }

  partition_keys {
    name = "geography_level"
    type = "string"
  }
}
