resource "aws_glue_catalog_table" "os_code_point_open_codepo" {
  name          = "os_code_point_open_codepo"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/os_code_point_open/codepo/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "postcode"
      type = "string"
    }
    columns {
      name = "positional_quality_indicator"
      type = "int"
    }
    columns {
      name = "eastings"
      type = "int"
    }
    columns {
      name = "northings"
      type = "int"
    }
    columns {
      name = "country_code"
      type = "string"
    }
    columns {
      name = "nhs_regional_ha_code"
      type = "string"
    }
    columns {
      name = "nhs_ha_code"
      type = "string"
    }
    columns {
      name = "admin_county_code"
      type = "string"
    }
    columns {
      name = "admin_district_code"
      type = "string"
    }
    columns {
      name = "admin_ward_code"
      type = "string"
    }
  }

  partition_keys {
    name = "postcode_area"
    type = "string"
  }
}
