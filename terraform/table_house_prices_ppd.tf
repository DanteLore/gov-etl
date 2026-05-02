resource "aws_glue_catalog_table" "house_prices_ppd" {
  name          = "house_prices_ppd"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"        = "parquet"
    "parquet.compression"   = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/house_prices/ppd/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "transaction_id"
      type = "string"
    }
    columns {
      name = "price"
      type = "bigint"
    }
    columns {
      name = "date_of_transfer"
      type = "string"
    }
    columns {
      name = "postcode"
      type = "string"
    }
    columns {
      name = "property_type"
      type = "string"
    }
    columns {
      name = "old_new"
      type = "string"
    }
    columns {
      name = "duration"
      type = "string"
    }
    columns {
      name = "paon"
      type = "string"
    }
    columns {
      name = "saon"
      type = "string"
    }
    columns {
      name = "street"
      type = "string"
    }
    columns {
      name = "locality"
      type = "string"
    }
    columns {
      name = "town_city"
      type = "string"
    }
    columns {
      name = "district"
      type = "string"
    }
    columns {
      name = "county"
      type = "string"
    }
    columns {
      name = "ppd_category_type"
      type = "string"
    }
    columns {
      name = "record_status"
      type = "string"
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }
}
