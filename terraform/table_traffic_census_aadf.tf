resource "aws_glue_catalog_table" "traffic_census_aadf" {
  name          = "traffic_census_aadf"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"        = "parquet"
    "parquet.compression"   = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/traffic_census/aadf/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "count_point_id"
      type = "int"
    }
    columns {
      name = "direction_of_travel"
      type = "string"
    }
    columns {
      name = "region_id"
      type = "int"
    }
    columns {
      name = "region_name"
      type = "string"
    }
    columns {
      name = "local_authority_id"
      type = "int"
    }
    columns {
      name = "local_authority_name"
      type = "string"
    }
    columns {
      name = "road_name"
      type = "string"
    }
    columns {
      name = "road_category"
      type = "string"
    }
    columns {
      name = "road_type"
      type = "string"
    }
    columns {
      name = "start_junction_road_name"
      type = "string"
    }
    columns {
      name = "end_junction_road_name"
      type = "string"
    }
    columns {
      name = "easting"
      type = "int"
    }
    columns {
      name = "northing"
      type = "int"
    }
    columns {
      name = "latitude"
      type = "double"
    }
    columns {
      name = "longitude"
      type = "double"
    }
    columns {
      name = "link_length_km"
      type = "double"
    }
    columns {
      name = "link_length_miles"
      type = "double"
    }
    columns {
      name = "pedal_cycles"
      type = "int"
    }
    columns {
      name = "two_wheeled_motor_vehicles"
      type = "int"
    }
    columns {
      name = "cars_and_taxis"
      type = "int"
    }
    columns {
      name = "buses_and_coaches"
      type = "int"
    }
    columns {
      name = "lgvs"
      type = "int"
    }
    columns {
      name = "hgvs_2_rigid_axle"
      type = "int"
    }
    columns {
      name = "hgvs_3_rigid_axle"
      type = "int"
    }
    columns {
      name = "hgvs_4_or_more_rigid_axle"
      type = "int"
    }
    columns {
      name = "hgvs_3_or_4_articulated_axle"
      type = "int"
    }
    columns {
      name = "hgvs_5_articulated_axle"
      type = "int"
    }
    columns {
      name = "hgvs_6_articulated_axle"
      type = "int"
    }
    columns {
      name = "all_hgvs"
      type = "int"
    }
    columns {
      name = "all_motor_vehicles"
      type = "int"
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }
}
