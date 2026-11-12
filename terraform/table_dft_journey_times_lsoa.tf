resource "aws_glue_catalog_table" "dft_journey_times_lsoa" {
  name          = "dft_journey_times_lsoa"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "DfT journey time statistics (JTS0501-JTS0509): modelled travel times from each LSOA in England to key services by public transport/walk, cycle, car and walking, long format"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/dft_journey_times_lsoa/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "lsoa_code"
      type = "string"
    }
    columns {
      name = "region"
      type = "string"
    }
    columns {
      name = "la_code"
      type = "string"
    }
    columns {
      name = "la_name"
      type = "string"
    }
    columns {
      name = "table_id"
      type = "string"
    }
    columns {
      name = "table_title"
      type = "string"
    }
    columns {
      name = "field"
      type = "string"
    }
    columns {
      name = "field_description"
      type = "string"
    }
    columns {
      name = "mode"
      type = "string"
    }
    columns {
      name = "value"
      type = "double"
    }
  }

  partition_keys {
    name = "edition_year"
    type = "string"
  }
}
