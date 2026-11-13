resource "aws_glue_catalog_table" "osm_paths" {
  name          = "osm_paths"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "OpenStreetMap ways tagged highway (roads, cycleways, footways, paths) with cycling and walking tags, node IDs and geometry, England"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/osm/paths/"
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
      name = "highway"
      type = "string"
    }
    columns {
      name = "name"
      type = "string"
    }
    columns {
      name = "ref"
      type = "string"
    }
    columns {
      name = "cycleway"
      type = "string"
    }
    columns {
      name = "cycleway_left"
      type = "string"
    }
    columns {
      name = "cycleway_right"
      type = "string"
    }
    columns {
      name = "cycleway_both"
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
      name = "segregated"
      type = "string"
    }
    columns {
      name = "surface"
      type = "string"
    }
    columns {
      name = "smoothness"
      type = "string"
    }
    columns {
      name = "lit"
      type = "string"
    }
    columns {
      name = "maxspeed"
      type = "string"
    }
    columns {
      name = "oneway"
      type = "string"
    }
    columns {
      name = "oneway_bicycle"
      type = "string"
    }
    columns {
      name = "access"
      type = "string"
    }
    columns {
      name = "motor_vehicle"
      type = "string"
    }
    columns {
      name = "width"
      type = "string"
    }
    columns {
      name = "incline"
      type = "string"
    }
    columns {
      name = "bridge"
      type = "string"
    }
    columns {
      name = "tunnel"
      type = "string"
    }
    columns {
      name = "layer"
      type = "string"
    }
    columns {
      name = "sidewalk"
      type = "string"
    }
    columns {
      name = "junction"
      type = "string"
    }
    columns {
      name = "area"
      type = "string"
    }
    columns {
      name = "tags_json"
      type = "string"
    }
    columns {
      name = "node_ids"
      type = "array<bigint>"
    }
    columns {
      name = "length_m"
      type = "double"
    }
    columns {
      name = "start_lon"
      type = "double"
    }
    columns {
      name = "start_lat"
      type = "double"
    }
    columns {
      name = "end_lon"
      type = "double"
    }
    columns {
      name = "end_lat"
      type = "double"
    }
    columns {
      name = "min_lon"
      type = "double"
    }
    columns {
      name = "min_lat"
      type = "double"
    }
    columns {
      name = "max_lon"
      type = "double"
    }
    columns {
      name = "max_lat"
      type = "double"
    }
    columns {
      name = "geometry_wkt"
      type = "string"
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
