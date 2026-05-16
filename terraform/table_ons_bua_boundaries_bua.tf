resource "aws_glue_catalog_table" "ons_bua_boundaries_bua" {
  name          = "ons_bua_boundaries_bua"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/ons_bua_boundaries/bua/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "bua24cd"
      type = "string"
    }
    columns {
      name = "bua24nm"
      type = "string"
    }
    columns {
      name = "geometry_wgs84_wkt"
      type = "string"
    }
    columns {
      name = "geometry_osgb_wkt"
      type = "string"
    }
    columns {
      name = "centre_e"
      type = "int"
    }
    columns {
      name = "centre_n"
      type = "int"
    }
    columns {
      name = "bbox_min_e"
      type = "int"
    }
    columns {
      name = "bbox_min_n"
      type = "int"
    }
    columns {
      name = "bbox_max_e"
      type = "int"
    }
    columns {
      name = "bbox_max_n"
      type = "int"
    }
  }
}
