resource "aws_glue_catalog_table" "osm_cycle_network_ends" {
  name          = "osm_cycle_network_ends"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "Places in the Thatcham area where a cycleway or shared path ends at a main road, a footway or nothing"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/osm_cycle_network_ends/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "node_id"
      type = "bigint"
    }
    columns {
      name = "lon"
      type = "double"
    }
    columns {
      name = "lat"
      type = "double"
    }
    columns {
      name = "ends_at"
      type = "string"
    }
    columns {
      name = "path_osm_id"
      type = "bigint"
    }
    columns {
      name = "path_name"
      type = "string"
    }
    columns {
      name = "path_provision"
      type = "string"
    }
    columns {
      name = "meets_name"
      type = "string"
    }
    columns {
      name = "meets_highway"
      type = "string"
    }
    columns {
      name = "crossing"
      type = "string"
    }
  }
}
