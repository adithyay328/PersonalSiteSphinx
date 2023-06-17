# OAC signing configuration for Distributions
resource "aws_cloudfront_origin_access_control" "cloudfrontS3OAC" {
  name = "${var.bucket_name}-cf-s3-oac"
  description = "The Origin Access Control for site source cloudfront distributions."
  origin_access_control_origin_type = "s3"
  signing_behavior = "always"
  signing_protocol = "sigv4"
}

# Caching Policy for our Cloudfront Distributions. This policy doesn't allow
# for super huge TTLs, allowing for faster site pushes
resource "aws_cloudfront_cache_policy" "distributionCachingPolicy" {
  name = "${var.bucket_name}-cf-cache-policy"
  comment = "This caching policy doesn't allow for massive TTLs, which makes it faster to update"

  min_ttl = 5
  default_ttl = 60
  max_ttl = 600

  parameters_in_cache_key_and_forwarded_to_origin {
    # Add any whitelisted cookies to the list below,
    # or set to none if empty
    cookies_config {
      cookie_behavior = "none"
    }
  
    # Add any whitelisted headers to the list below,
    # or set to none if empty
    headers_config {
      header_behavior = "whitelist"
      headers {
        items = ["Strict-Transport-Security"]
      }
    }
    
    # Add any whitelisted query strings to the list below,
    # or set to none if empty
    query_strings_config {
      query_string_behavior = "none"
    }
  }
}

resource "aws_cloudfront_response_headers_policy" "cloudfront-hsts-headers" {
  name = "${var.bucket_name}-cf-hsts-headers"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = 31536000
      override = true
      preload = false
    }
  }
}