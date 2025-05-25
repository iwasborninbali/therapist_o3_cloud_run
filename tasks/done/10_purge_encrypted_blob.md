# Task 10: Purge Encrypted Blob Artifacts

**Status**: in-progress  
**Assigned**: gemini_1  
**Created**: 2025-05-25

## Objective
Remove all encrypted blob artifacts and related code to maintain ADR compliance with the new YAML env-vars approach.

## Requirements
1. Delete `firebase_creds_encrypted.bin`
2. Update .gitignore/.dockerignore with `*creds_encrypted*.bin` rule
3. Remove encryption logic from config.py
4. Update scripts/local_deploy.sh 
5. Update README & ADR-0002 documentation
6. Add CI guard for *.bin files
7. Update tests/conftest.py if needed
8. Run pytest & lint

## Implementation
- [x] Delete firebase_creds_encrypted.bin
- [x] Update .gitignore/.dockerignore  
- [x] Clean config.py (remove decrypt_firebase_credentials)
- [ ] Update scripts/local_deploy.sh
- [ ] Update README & ADR-0002
- [ ] Add CI guard
- [ ] Update tests
- [ ] Run pytest & lint

## Files Modified
- firebase_creds_encrypted.bin (deleted)
- .gitignore
- .dockerignore  
- config.py
- scripts/local_deploy.sh
- README.md
- docs/ADR-*
- .github/workflows/*
- tests/* 