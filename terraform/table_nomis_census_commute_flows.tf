resource "aws_glue_catalog_table" "nomis_census_commute_flows" {
  name          = "nomis_census_commute_flows"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "Census 2021 ODWP01EW home to workplace flows, England and Wales, by MSOA and local authority"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/nomis_census_commute_flows/"
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
      name = "place_of_work_code"
      type = "int"
    }
    columns {
      name = "place_of_work_name"
      type = "string"
    }
    columns {
      name = "count"
      type = "int"
    }
  }

  partition_keys {
    name = "geography_level"
    type = "string"
  }
}
