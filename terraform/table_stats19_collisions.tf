resource "aws_glue_catalog_table" "stats19_collisions" {
  name          = "stats19_collisions"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "DfT road safety data (STATS19): every reported injury road collision in Great Britain since 1979, with location"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/stats19/stats19_collisions/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "collision_index"
      type = "string"
    }
    columns {
      name = "collision_ref_no"
      type = "string"
    }
    columns {
      name = "location_easting_osgr"
      type = "int"
    }
    columns {
      name = "location_northing_osgr"
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
      name = "police_force"
      type = "int"
    }
    columns {
      name = "collision_severity"
      type = "int"
    }
    columns {
      name = "number_of_vehicles"
      type = "int"
    }
    columns {
      name = "number_of_casualties"
      type = "int"
    }
    columns {
      name = "date"
      type = "date"
    }
    columns {
      name = "day_of_week"
      type = "int"
    }
    columns {
      name = "time"
      type = "string"
    }
    columns {
      name = "local_authority_district"
      type = "int"
    }
    columns {
      name = "local_authority_ons_district"
      type = "string"
    }
    columns {
      name = "local_authority_highway"
      type = "string"
    }
    columns {
      name = "local_authority_highway_current"
      type = "string"
    }
    columns {
      name = "first_road_class"
      type = "int"
    }
    columns {
      name = "first_road_number"
      type = "int"
    }
    columns {
      name = "road_type"
      type = "int"
    }
    columns {
      name = "speed_limit"
      type = "int"
    }
    columns {
      name = "junction_detail_historic"
      type = "int"
    }
    columns {
      name = "junction_detail"
      type = "int"
    }
    columns {
      name = "junction_control"
      type = "int"
    }
    columns {
      name = "second_road_class"
      type = "int"
    }
    columns {
      name = "second_road_number"
      type = "int"
    }
    columns {
      name = "pedestrian_crossing_human_control_historic"
      type = "int"
    }
    columns {
      name = "pedestrian_crossing_physical_facilities_historic"
      type = "int"
    }
    columns {
      name = "pedestrian_crossing"
      type = "int"
    }
    columns {
      name = "light_conditions"
      type = "int"
    }
    columns {
      name = "weather_conditions"
      type = "int"
    }
    columns {
      name = "road_surface_conditions"
      type = "int"
    }
    columns {
      name = "special_conditions_at_site"
      type = "int"
    }
    columns {
      name = "carriageway_hazards_historic"
      type = "int"
    }
    columns {
      name = "carriageway_hazards"
      type = "int"
    }
    columns {
      name = "urban_or_rural_area"
      type = "int"
    }
    columns {
      name = "did_police_officer_attend_scene_of_accident"
      type = "int"
    }
    columns {
      name = "trunk_road_flag"
      type = "int"
    }
    columns {
      name = "lsoa_of_accident_location"
      type = "string"
    }
    columns {
      name = "enhanced_severity_collision"
      type = "int"
    }
    columns {
      name = "collision_injury_based"
      type = "int"
    }
    columns {
      name = "collision_adjusted_severity_serious"
      type = "double"
    }
    columns {
      name = "collision_adjusted_severity_slight"
      type = "double"
    }
  }

  partition_keys {
    name = "collision_year"
    type = "string"
  }
}
