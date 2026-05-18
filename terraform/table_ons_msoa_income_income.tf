resource "aws_glue_catalog_table" "ons_msoa_income_income" {
  name          = "ons_msoa_income_income"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/ons_msoa_income/income/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "msoa21cd"
      type = "string"
    }
    columns {
      name = "msoa21nm"
      type = "string"
    }
    columns {
      name = "lad_code"
      type = "string"
    }
    columns {
      name = "lad_name"
      type = "string"
    }
    columns {
      name = "rgn_code"
      type = "string"
    }
    columns {
      name = "rgn_name"
      type = "string"
    }
    columns {
      name = "total_annual_income"
      type = "double"
    }
    columns {
      name = "total_annual_income_upper_ci"
      type = "double"
    }
    columns {
      name = "total_annual_income_lower_ci"
      type = "double"
    }
    columns {
      name = "total_annual_income_ci"
      type = "double"
    }
    columns {
      name = "net_annual_income"
      type = "double"
    }
    columns {
      name = "net_annual_income_upper_ci"
      type = "double"
    }
    columns {
      name = "net_annual_income_lower_ci"
      type = "double"
    }
    columns {
      name = "net_annual_income_ci"
      type = "double"
    }
    columns {
      name = "net_income_before_housing"
      type = "double"
    }
    columns {
      name = "net_income_before_housing_upper_ci"
      type = "double"
    }
    columns {
      name = "net_income_before_housing_lower_ci"
      type = "double"
    }
    columns {
      name = "net_income_before_housing_ci"
      type = "double"
    }
    columns {
      name = "net_income_after_housing"
      type = "double"
    }
    columns {
      name = "net_income_after_housing_upper_ci"
      type = "double"
    }
    columns {
      name = "net_income_after_housing_lower_ci"
      type = "double"
    }
    columns {
      name = "net_income_after_housing_ci"
      type = "double"
    }
  }
}
