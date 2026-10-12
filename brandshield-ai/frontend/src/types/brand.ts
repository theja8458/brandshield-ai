export interface OfficialSocialAsset {
  asset_id?: string;
  platform: string;
  display_name: string;
  canonical_profile_url: string;
  normalized_handle: string;
  stable_account_id?: string;
}

export interface OfficialAppAsset {
  asset_id?: string;
  store: string;
  app_name: string;
  canonical_listing_url: string;
  package_or_bundle_id: string;
  trusted_publisher_name: string;
  trusted_publisher_id?: string;
  icon_reference?: string;
  icon_hash?: string;
}

export interface OfficialLogo {
  image_reference?: string;
  image_hash: string;
  hash_algorithm?: string;
}

export interface Brand {
  brand_id: string;
  name: string;
  description: string;
  official_website: string;
  official_domains: string[];
  aliases: string[];
  keywords: string[];
  safe_list: string[];
  official_logo?: OfficialLogo;
  official_social_assets: OfficialSocialAsset[];
  official_app_assets: OfficialAppAsset[];
  status: string;
  dataset_id?: string;
  source_type: string;
  is_demo_data?: boolean;
  is_synthetic?: boolean;
  created_at: string;
  updated_at: string;
}

export interface OfficialEvaluationResult {
  status: 'OFFICIAL_EXCLUDED' | 'REVIEW_REQUIRED' | 'SAFE_LISTED' | 'NOT_OFFICIAL';
  is_excluded_from_scoring: boolean;
  matched_asset_id?: string;
  reason: string;
  conflict_details?: string;
}
