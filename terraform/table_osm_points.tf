resource "aws_glue_catalog_table" "osm_points" {
  name          = "osm_points"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "OpenStreetMap crossings, signals, barriers, level crossings, cycle parking and schools, England"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/osm/points/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "osm_id"
      type = "bigint"
    }
    columns {
      name = "osm_type"
      type = "string"
    }
    columns {
      name = "feature"
      type = "string"
    }
    columns {
      name = "highway"
      type = "string"
    }
    columns {
      name = "crossing"
      type = "string"
    }
    columns {
      name = "crossing_ref"
      type = "string"
    }
    columns {
      name = "barrier"
      type = "string"
    }
    columns {
      name = "railway"
      type = "string"
    }
    columns {
      name = "amenity"
      type = "string"
    }
    columns {
      name = "bicycle"
      type = "string"
    }
    columns {
      name = "foot"
      type = "string"
    }
    columns {
      name = "kerb"
      type = "string"
    }
    columns {
      name = "capacity"
      type = "string"
    }
    columns {
      name = "covered"
      type = "string"
    }
    columns {
      name = "bicycle_parking"
      type = "string"
    }
    columns {
      name = "name"
      type = "string"
    }
    columns {
      name = "tags_json"
      type = "string"
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
      name = "snapshot_date"
      type = "string"
    }
  }

  partition_keys {
    name = "grid_e"
    type = "int"
  }

  partition_keys {
    name = "grid_n"
    type = "int"
  }
}
