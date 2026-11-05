terraform {
  required_version = ">= 1.6" # older versions can't read the SSO sso-session profile

  backend "s3" {
    bucket  = "dantelore.tfstate"
    key     = "gov-etl.tfstate"
    region  = "eu-west-1"
    profile = "dantelore"
  }
}
