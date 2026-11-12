resource "aws_glue_catalog_table" "naptan_stops" {
  name          = "naptan_stops"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "NaPTAN: every public transport stop in Great Britain (bus stops, stations, tram and ferry stops) with location, partitioned by 100km grid tile"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/naptan_stops/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "atco_code"
      type = "string"
    }
    columns {
      name = "naptan_code"
      type = "string"
    }
    columns {
      name = "plate_code"
      type = "string"
    }
    columns {
      name = "cleardown_code"
      type = "string"
    }
    columns {
      name = "common_name"
      type = "string"
    }
    columns {
      name = "common_name_lang"
      type = "string"
    }
    columns {
      name = "short_common_name"
      type = "string"
    }
    columns {
      name = "short_common_name_lang"
      type = "string"
    }
    columns {
      name = "landmark"
      type = "string"
    }
    columns {
      name = "landmark_lang"
      type = "string"
    }
    columns {
      name = "street"
      type = "string"
    }
    columns {
      name = "street_lang"
      type = "string"
    }
    columns {
      name = "crossing"
      type = "string"
    }
    columns {
      name = "crossing_lang"
      type = "string"
    }
    columns {
      name = "indicator"
      type = "string"
    }
    columns {
      name = "indicator_lang"
      type = "string"
    }
    columns {
      name = "bearing"
      type = "string"
    }
    columns {
      name = "nptg_locality_code"
      type = "string"
    }
    columns {
      name = "locality_name"
      type = "string"
    }
    columns {
      name = "parent_locality_name"
      type = "string"
    }
    columns {
      name = "grand_parent_locality_name"
      type = "string"
    }
    columns {
      name = "town"
      type = "string"
    }
    columns {
      name = "town_lang"
      type = "string"
    }
    columns {
      name = "suburb"
      type = "string"
    }
    columns {
      name = "suburb_lang"
      type = "string"
    }
    columns {
      name = "locality_centre"
      type = "boolean"
    }
    columns {
      name = "grid_type"
      type = "string"
    }
    columns {
      name = "x_coordinate"
      type = "int"
    }
    columns {
      name = "y_coordinate"
      type = "int"
    }
    columns {
      name = "longitude"
      type = "double"
    }
    columns {
      name = "latitude"
      type = "double"
    }
    columns {
      name = "stop_type"
      type = "string"
    }
    columns {
      name = "bus_stop_type"
      type = "string"
    }
    columns {
      name = "timing_status"
      type = "string"
    }
    columns {
      name = "default_wait_time"
      type = "string"
    }
    columns {
      name = "notes"
      type = "string"
    }
    columns {
      name = "notes_lang"
      type = "string"
    }
    columns {
      name = "administrative_area_code"
      type = "string"
    }
    columns {
      name = "creation_date_time"
      type = "timestamp"
    }
    columns {
      name = "modification_date_time"
      type = "timestamp"
    }
    columns {
      name = "revision_number"
      type = "string"
    }
    columns {
      name = "modification"
      type = "string"
    }
    columns {
      name = "status"
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
