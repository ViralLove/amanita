CREATE TABLE IF NOT EXISTS public.uploads (
    upload_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    payload_hash    TEXT,
    payload_size    BIGINT,
    tags_snapshot   JSONB,
    anchor          TEXT,
    expires_at      TIMESTAMPTZ,
    owner_address   TEXT,
    item_id         TEXT,
    bundle_tx_id    TEXT,
    status          TEXT NOT NULL,
    failure_reason  TEXT,
    failure_code    TEXT,
    activity_id     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.uploads IS 'Upload flow (Arweave data items): prepare → signed_validated → queued_for_publish → published → finalized | failed. activity_id links to Activity (draft = activity with active=false).';
COMMENT ON COLUMN public.uploads.activity_id IS 'Optional link to Activity (on_chain.id); no separate draft_id.';
COMMENT ON COLUMN public.uploads.status IS 'One of: prepared, signed_validated, queued_for_publish, published, finalized, failed.';

CREATE INDEX IF NOT EXISTS idx_uploads_user_id ON public.uploads (user_id);
CREATE INDEX IF NOT EXISTS idx_uploads_status ON public.uploads (status);
CREATE INDEX IF NOT EXISTS idx_uploads_activity_id ON public.uploads (activity_id) WHERE activity_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_uploads_expires_at ON public.uploads (expires_at) WHERE expires_at IS NOT NULL;
