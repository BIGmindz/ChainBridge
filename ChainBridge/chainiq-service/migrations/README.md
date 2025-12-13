# ChainIQ Service Migrations

This directory contains database migration scripts for the ChainIQ service.

## Running Migrations

### PostgreSQL
```bash
psql -h localhost -U chainiq_user -d chainiq_db -f migrations/001_shadow_mode_tables.sql
```

### Using environment variable
```bash
export DATABASE_URL="postgresql://user:pass@localhost/chainiq"
psql $DATABASE_URL -f migrations/001_shadow_mode_tables.sql
```

## Migration History

- **001_shadow_mode_tables.sql** - Creates risk_shadow_events table for shadow mode tracking

## Future Migrations

When adding new migrations:
1. Use sequential numbering: 002_*, 003_*, etc.
2. Include rollback script (down migration)
3. Test on local/dev environment first
4. Document changes in this README
