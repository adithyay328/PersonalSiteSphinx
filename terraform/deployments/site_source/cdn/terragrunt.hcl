include {
  path = find_in_parent_folders("root.hcl")
}

inputs = {
  bucket_name = "sphinx_site_template_cdn_bucket"
  cloudfront_aliases = ["cdn.adiy.io", "www.cdn.adiy.io"]
  viewer_request_function_arn_list = []
  cloudfront_path_prefix = null
}