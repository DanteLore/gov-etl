resource "aws_glue_catalog_table" "ons_census_area_lookup_2011_2021" {
  name          = "ons_census_area_lookup_2011_2021"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "ONS lookups from 2011 to 2021 Census output areas, LSOAs and MSOAs, England and Wales"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/ons_census_area_lookup_2011_2021/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "code_2011"
      type = "string"
    }
    columns {
      name = "name_2011"
      type = "string"
    }
    columns {
      name = "code_2021"
      type = "string"
    }
    columns {
      name = "name_2021"
      type = "string"
    }
    columns {
      name = "change_indicator"
      type = "string"
    }
    columns {
      name = "lad22_code"
      type = "string"
    }
    columns {
      name = "lad22_name"
      type = "string"
    }
  }

  partition_keys {
    name = "geography_level"
    type = "string"
  }
}
