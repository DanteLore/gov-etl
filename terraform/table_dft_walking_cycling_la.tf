resource "aws_glue_catalog_table" "dft_walking_cycling_la" {
  name          = "dft_walking_cycling_la"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "DfT walking and cycling statistics (CW0301-CW0303 via CW0307): share of adults walking or cycling by purpose and frequency, England, regions and local authorities, yearly from 2016 (Active Lives Survey)"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/dft_walking_cycling_la/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "area_code"
      type = "string"
    }
    columns {
      name = "area_name"
      type = "string"
    }
    columns {
      name = "area_class"
      type = "string"
    }
    columns {
      name = "mode"
      type = "string"
    }
    columns {
      name = "purpose"
      type = "string"
    }
    columns {
      name = "frequency"
      type = "string"
    }
    columns {
      name = "year"
      type = "int"
    }
    columns {
      name = "pct"
      type = "double"
    }
    columns {
      name = "ci_margin_pct"
      type = "double"
    }
    columns {
      name = "sample_size"
      type = "int"
    }
    columns {
      name = "is_suppressed"
      type = "boolean"
    }
    columns {
      name = "edition_published"
      type = "string"
    }
  }
}
