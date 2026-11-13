resource "aws_glue_catalog_table" "pct_commute_zones" {
  name          = "pct_commute_zones"
  database_name = "incoming"
  table_type    = "EXTERNAL_TABLE"
  description   = "Propensity to Cycle Tool: cycling to work now (Census 2011) and under each scenario, by MSOA and LSOA of residence, England and Wales"

  parameters = {
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://dantelore.data.incoming/pct_commute_zones/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "geo_code"
      type = "string"
    }
    columns {
      name = "geo_name"
      type = "string"
    }
    columns {
      name = "lad11cd"
      type = "string"
    }
    columns {
      name = "lad_name"
      type = "string"
    }
    columns {
      name = "all"
      type = "double"
    }
    columns {
      name = "bicycle"
      type = "double"
    }
    columns {
      name = "foot"
      type = "double"
    }
    columns {
      name = "car_driver"
      type = "double"
    }
    columns {
      name = "car_passenger"
      type = "double"
    }
    columns {
      name = "motorbike"
      type = "double"
    }
    columns {
      name = "train_tube"
      type = "double"
    }
    columns {
      name = "bus"
      type = "double"
    }
    columns {
      name = "taxi_other"
      type = "double"
    }
    columns {
      name = "govtarget_slc"
      type = "double"
    }
    columns {
      name = "govtarget_sic"
      type = "double"
    }
    columns {
      name = "govtarget_slw"
      type = "double"
    }
    columns {
      name = "govtarget_siw"
      type = "double"
    }
    columns {
      name = "govtarget_sld"
      type = "double"
    }
    columns {
      name = "govtarget_sid"
      type = "double"
    }
    columns {
      name = "govtarget_slp"
      type = "double"
    }
    columns {
      name = "govtarget_sip"
      type = "double"
    }
    columns {
      name = "govtarget_slm"
      type = "double"
    }
    columns {
      name = "govtarget_sim"
      type = "double"
    }
    columns {
      name = "govtarget_slpt"
      type = "double"
    }
    columns {
      name = "govtarget_sipt"
      type = "double"
    }
    columns {
      name = "govnearmkt_slc"
      type = "double"
    }
    columns {
      name = "govnearmkt_sic"
      type = "double"
    }
    columns {
      name = "govnearmkt_slw"
      type = "double"
    }
    columns {
      name = "govnearmkt_siw"
      type = "double"
    }
    columns {
      name = "govnearmkt_sld"
      type = "double"
    }
    columns {
      name = "govnearmkt_sid"
      type = "double"
    }
    columns {
      name = "govnearmkt_slp"
      type = "double"
    }
    columns {
      name = "govnearmkt_sip"
      type = "double"
    }
    columns {
      name = "govnearmkt_slm"
      type = "double"
    }
    columns {
      name = "govnearmkt_sim"
      type = "double"
    }
    columns {
      name = "govnearmkt_slpt"
      type = "double"
    }
    columns {
      name = "govnearmkt_sipt"
      type = "double"
    }
    columns {
      name = "gendereq_slc"
      type = "double"
    }
    columns {
      name = "gendereq_sic"
      type = "double"
    }
    columns {
      name = "gendereq_slw"
      type = "double"
    }
    columns {
      name = "gendereq_siw"
      type = "double"
    }
    columns {
      name = "gendereq_sld"
      type = "double"
    }
    columns {
      name = "gendereq_sid"
      type = "double"
    }
    columns {
      name = "gendereq_slp"
      type = "double"
    }
    columns {
      name = "gendereq_sip"
      type = "double"
    }
    columns {
      name = "gendereq_slm"
      type = "double"
    }
    columns {
      name = "gendereq_sim"
      type = "double"
    }
    columns {
      name = "gendereq_slpt"
      type = "double"
    }
    columns {
      name = "gendereq_sipt"
      type = "double"
    }
    columns {
      name = "dutch_slc"
      type = "double"
    }
    columns {
      name = "dutch_sic"
      type = "double"
    }
    columns {
      name = "dutch_slw"
      type = "double"
    }
    columns {
      name = "dutch_siw"
      type = "double"
    }
    columns {
      name = "dutch_sld"
      type = "double"
    }
    columns {
      name = "dutch_sid"
      type = "double"
    }
    columns {
      name = "dutch_slp"
      type = "double"
    }
    columns {
      name = "dutch_sip"
      type = "double"
    }
    columns {
      name = "dutch_slm"
      type = "double"
    }
    columns {
      name = "dutch_sim"
      type = "double"
    }
    columns {
      name = "dutch_slpt"
      type = "double"
    }
    columns {
      name = "dutch_sipt"
      type = "double"
    }
    columns {
      name = "ebike_slc"
      type = "double"
    }
    columns {
      name = "ebike_sic"
      type = "double"
    }
    columns {
      name = "ebike_slw"
      type = "double"
    }
    columns {
      name = "ebike_siw"
      type = "double"
    }
    columns {
      name = "ebike_sld"
      type = "double"
    }
    columns {
      name = "ebike_sid"
      type = "double"
    }
    columns {
      name = "ebike_slp"
      type = "double"
    }
    columns {
      name = "ebike_sip"
      type = "double"
    }
    columns {
      name = "ebike_slm"
      type = "double"
    }
    columns {
      name = "ebike_sim"
      type = "double"
    }
    columns {
      name = "ebike_slpt"
      type = "double"
    }
    columns {
      name = "ebike_sipt"
      type = "double"
    }
    columns {
      name = "base_slcyclehours"
      type = "double"
    }
    columns {
      name = "govtarget_sicyclehours"
      type = "double"
    }
    columns {
      name = "govnearmkt_sicyclehours"
      type = "double"
    }
    columns {
      name = "gendereq_sicyclehours"
      type = "double"
    }
    columns {
      name = "dutch_sicyclehours"
      type = "double"
    }
    columns {
      name = "ebike_sicyclehours"
      type = "double"
    }
    columns {
      name = "base_sldeath"
      type = "double"
    }
    columns {
      name = "base_slyll"
      type = "double"
    }
    columns {
      name = "base_slvalueyll"
      type = "double"
    }
    columns {
      name = "base_slsickdays"
      type = "double"
    }
    columns {
      name = "base_slvaluesick"
      type = "double"
    }
    columns {
      name = "base_slvaluecomb"
      type = "double"
    }
    columns {
      name = "govtarget_sideath"
      type = "double"
    }
    columns {
      name = "govtarget_siyll"
      type = "double"
    }
    columns {
      name = "govtarget_sivalueyll"
      type = "double"
    }
    columns {
      name = "govtarget_sisickdays"
      type = "double"
    }
    columns {
      name = "govtarget_sivaluesick"
      type = "double"
    }
    columns {
      name = "govtarget_sivaluecomb"
      type = "double"
    }
    columns {
      name = "govnearmkt_sideath"
      type = "double"
    }
    columns {
      name = "govnearmkt_siyll"
      type = "double"
    }
    columns {
      name = "govnearmkt_sivalueyll"
      type = "double"
    }
    columns {
      name = "govnearmkt_sisickdays"
      type = "double"
    }
    columns {
      name = "govnearmkt_sivaluesick"
      type = "double"
    }
    columns {
      name = "govnearmkt_sivaluecomb"
      type = "double"
    }
    columns {
      name = "gendereq_sideath"
      type = "double"
    }
    columns {
      name = "gendereq_siyll"
      type = "double"
    }
    columns {
      name = "gendereq_sivalueyll"
      type = "double"
    }
    columns {
      name = "gendereq_sisickdays"
      type = "double"
    }
    columns {
      name = "gendereq_sivaluesick"
      type = "double"
    }
    columns {
      name = "gendereq_sivaluecomb"
      type = "double"
    }
    columns {
      name = "dutch_sideath"
      type = "double"
    }
    columns {
      name = "dutch_siyll"
      type = "double"
    }
    columns {
      name = "dutch_sivalueyll"
      type = "double"
    }
    columns {
      name = "dutch_sisickdays"
      type = "double"
    }
    columns {
      name = "dutch_sivaluesick"
      type = "double"
    }
    columns {
      name = "dutch_sivaluecomb"
      type = "double"
    }
    columns {
      name = "ebike_sideath"
      type = "double"
    }
    columns {
      name = "ebike_siyll"
      type = "double"
    }
    columns {
      name = "ebike_sivalueyll"
      type = "double"
    }
    columns {
      name = "ebike_sisickdays"
      type = "double"
    }
    columns {
      name = "ebike_sivaluesick"
      type = "double"
    }
    columns {
      name = "ebike_sivaluecomb"
      type = "double"
    }
    columns {
      name = "base_slcarkm"
      type = "double"
    }
    columns {
      name = "base_slco2"
      type = "double"
    }
    columns {
      name = "govtarget_sicarkm"
      type = "double"
    }
    columns {
      name = "govtarget_sico2"
      type = "double"
    }
    columns {
      name = "govnearmkt_sicarkm"
      type = "double"
    }
    columns {
      name = "govnearmkt_sico2"
      type = "double"
    }
    columns {
      name = "gendereq_sicarkm"
      type = "double"
    }
    columns {
      name = "gendereq_sico2"
      type = "double"
    }
    columns {
      name = "dutch_sicarkm"
      type = "double"
    }
    columns {
      name = "dutch_sico2"
      type = "double"
    }
    columns {
      name = "ebike_sicarkm"
      type = "double"
    }
    columns {
      name = "ebike_sico2"
      type = "double"
    }
    columns {
      name = "perc_rf_dist_u10km"
      type = "double"
    }
    columns {
      name = "avslope_perc_u10km"
      type = "double"
    }
  }

  partition_keys {
    name = "geography_level"
    type = "string"
  }
}
