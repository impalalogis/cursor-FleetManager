from django.db import migrations

SQL = r"""
DO $$
DECLARE
    fkname text;
BEGIN
    -- Try to drop FK on doc_type_id if it exists
    SELECT conname
      INTO fkname
      FROM pg_constraint
     WHERE conrelid = 'public.vehicle'::regclass
       AND contype = 'f'
       AND conkey = ARRAY[
            (SELECT attnum
               FROM pg_attribute
              WHERE attrelid = 'public.vehicle'::regclass
                AND attname = 'doc_type_id')
       ]
     LIMIT 1;

    IF fkname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE public.vehicle DROP CONSTRAINT %I;', fkname);
    END IF;
EXCEPTION
    WHEN undefined_table THEN
        -- table doesn't exist in this DB; ignore
        NULL;
END $$;

-- Now drop the stray columns if they exist
ALTER TABLE public.vehicle DROP COLUMN IF EXISTS doc_type_id;
ALTER TABLE public.vehicle DROP COLUMN IF EXISTS file;
"""

class Migration(migrations.Migration):

    dependencies = [
        ('entity', '0006_broker_pan_document_broker_pan_number_and_more'),
    ]

    operations = [
        migrations.RunSQL(SQL, reverse_sql="""
            -- Reverse (optional): recreate the columns empty if someone rolls back
            ALTER TABLE public.vehicle ADD COLUMN IF NOT EXISTS doc_type_id bigint;
            ALTER TABLE public.vehicle ADD COLUMN IF NOT EXISTS file varchar(100);
        """),
    ]
