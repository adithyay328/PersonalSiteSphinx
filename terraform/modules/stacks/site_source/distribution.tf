# Cloudfront distribution and config for this site source

# Our actual cloudfront distribution for this site source
resource "aws_cloudfront_distribution" "siteSourceDistribution" {
  origin {
    domain_name = aws_s3_bucket.siteSourceBucket.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.cloudfrontS3OAC.id
    origin_id = "Site Source Bucket"
    origin_path = var.cloudfront_path_prefix
  }

  aliases = var.cloudfront_aliases

  enabled = true
  is_ipv6_enabled = true
  default_root_object = var.cloudfront_default_root_object
  
  # Configuring caching bevhaior
  default_cache_behavior {
    allowed_methods = ["GET", "HEAD"]
    cached_methods = ["GET", "HEAD"]
    target_origin_id = "Site Source Bucket"

    # Linking to our caching policy
    cache_policy_id = aws_cloudfront_cache_policy.distributionCachingPolicy.id

    # Linking to our header policy
    response_headers_policy_id = aws_cloudfront_response_headers_policy.cloudfront-hsts-headers.id
    
    # Preferring HTTPS, which means that the initial request is the only
    # point of vulnerability with HSTS enabled
    viewer_protocol_policy = "redirect-to-https"

    # Optionally set a function association for viewer request;
    # reads from a list to allow this to be disabled
    dynamic "function_association" {
      for_each = var.viewer_request_function_arn_list

      content {
        event_type = "viewer-request"
        function_arn = var.viewer_request_function_arn_list[0]
      }
    }
  }

  # Don't want any geo restrictions
  restrictions {
    geo_restriction {
      locations = []
      restriction_type = "none"
    }
  }

  # Only want to cache in US and Europe
  price_class = "PriceClass_100"

  # Want to support the latest versions of HTTP
  http_version = "http2and3"

  # Configuring acm certificate and SSL options; common for all distributions
  viewer_certificate {
    acm_certificate_arn = aws_acm_certificate.prodSiteSourceACMCert.arn
    ssl_support_method = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  # Configuring custom error page; S3 throws a 403, we just turn that into a
  # 404 and return the error page. This is dynamic to allow us to disable this
  # by just setting the page path list to an empty list
  custom_error_response {
    error_code = "404"
    response_code = "404"
    response_page_path = "/404/index.html"
  }
}