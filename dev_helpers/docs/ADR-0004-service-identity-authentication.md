# ADR-0004: Use Service Identity for Firebase Authentication

## Status
Accepted

## Context
Previously, the application used explicit Firebase credentials via `GOOGLE_APPLICATION_CREDENTIALS` environment variable, which required storing sensitive JSON credentials in environment variables. This approach had several issues:

1. **Security concerns**: Storing private keys in environment variables
2. **Google Cloud best practices**: Google recommends using service identity instead of explicit credentials
3. **Warning messages**: Cloud Run showed warnings about using `GOOGLE_APPLICATION_CREDENTIALS`
4. **Complexity**: Managing credential files and environment variables

## Decision
We will use Cloud Run service identity for Firebase authentication instead of explicit credentials.

### Implementation Details

1. **Created dedicated service account**: `therapist-o3-service@therapist-o3.iam.gserviceaccount.com`
2. **Granted Firebase permissions**: Added `roles/firebase.admin` role on the Firebase project (`ales-f75a1`)
3. **Updated Cloud Run service**: Configured to use the new service account as service identity
4. **Modified application code**: Updated `config.py` to detect Cloud Run environment and use service identity
5. **Removed explicit credentials**: No longer setting `GOOGLE_APPLICATION_CREDENTIALS` in Cloud Run

### Project Structure
- **Cloud Run project**: `therapist-o3` (for compute resources)
- **Firebase project**: `ales-f75a1` (for data storage)
- **Service account**: `therapist-o3-service@therapist-o3.iam.gserviceaccount.com`

## Consequences

### Positive
- **Better security**: No private keys stored in environment variables
- **Compliance**: Follows Google Cloud best practices
- **Simplified deployment**: No need to manage credential files
- **Automatic authentication**: Cloud Run automatically provides access tokens
- **No warnings**: Eliminates Google Cloud warnings about credential usage

### Negative
- **Local development complexity**: Still requires explicit credentials for local testing
- **Cross-project setup**: Requires IAM configuration across two Google Cloud projects

### Migration Impact
- **Environment variables**: Removed `GOOGLE_APPLICATION_CREDENTIALS` from Cloud Run
- **Code changes**: Updated `config.py` to handle both Cloud Run and local development
- **Deployment scripts**: Updated to use correct project IDs and service accounts

## Implementation Commands Used

```bash
# Create dedicated service account
gcloud iam service-accounts create therapist-o3-service \
  --display-name="Therapist O3 Service Account" \
  --description="Service account for therapist-o3 Cloud Run service"

# Grant Firebase permissions
gcloud projects add-iam-policy-binding ales-f75a1 \
  --member="serviceAccount:therapist-o3-service@therapist-o3.iam.gserviceaccount.com" \
  --role="roles/firebase.admin"

# Update Cloud Run service to use new service account
gcloud run services update therapist-o3 \
  --region=us-central1 \
  --service-account=therapist-o3-service@therapist-o3.iam.gserviceaccount.com

# Remove explicit credentials
gcloud run services update therapist-o3 \
  --region=us-central1 \
  --remove-env-vars="GOOGLE_APPLICATION_CREDENTIALS"
```

## References
- [Google Cloud Service Identity Documentation](https://cloud.google.com/run/docs/securing/service-identity)
- [Firebase Admin SDK Authentication](https://firebase.google.com/docs/admin/setup#initialize_the_sdk_in_non-google_environments) 