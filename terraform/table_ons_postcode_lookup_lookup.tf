resource "aws_glue_catalog_table" "ons_postcode_lookup_lookup" {
  name          = "ons_postcode_lookup_lookup"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/ons_postcode_lookup/lookup/"
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
      name = "msoa21cd"
      type = "string"
    }
    columns {
      name = "msoa21nm"
      type = "string"
    }
    columns {
      name = "lad22cd"
      type = "string"
    }
    columns {
      name = "lad22nm"
      type = "string"
    }
    columns {
      name = "ctyua22cd"
      type = "string"
    }
    columns {
      name = "ctyua22nm"
      type = "string"
    }
    columns {
      name = "rgn22cd"
      type = "string"
    }
    columns {
      name = "rgn22nm"
      type = "string"
    }
    columns {
      name = "ctry22cd"
      type = "string"
    }
    columns {
      name = "ctry22nm"
      type = "string"
    }
  }

  partition_keys {
    name = "postcode_area"
    type = "string"
  }
}
