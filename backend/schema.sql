CREATE TABLE IF NOT EXISTS rehearsal_venues (
 code text PRIMARY KEY,title text NOT NULL, covered boolean NOT NULL, max_heads int NOT NULL CHECK(max_heads>0),
 rate_per_half int NOT NULL CHECK(rate_per_half>=0), neighborhood text NOT NULL
);
CREATE TABLE IF NOT EXISTS historical_blocks (
 on_day date, half_from smallint CHECK(half_from BETWEEN 0 AND 47),
 temp_c real NOT NULL CHECK(temp_c BETWEEN -15 AND 55), humidity int NOT NULL CHECK(humidity BETWEEN 0 AND 100),
 source text NOT NULL, PRIMARY KEY(on_day,half_from)
);
CREATE TABLE IF NOT EXISTS practice_holds (
 code text PRIMARY KEY,title text NOT NULL,on_day date NOT NULL, original text NOT NULL REFERENCES rehearsal_venues(code),
 backup text NOT NULL REFERENCES rehearsal_venues(code), from_block smallint NOT NULL,to_block smallint NOT NULL,
 heads int NOT NULL CHECK(heads>0),state text NOT NULL CHECK(state IN ('held','proposed','closed')),
 CHECK(0<=from_block AND from_block<to_block AND to_block<=48),CHECK(original<>backup)
);
CREATE TABLE IF NOT EXISTS analog_replays (
 code text PRIMARY KEY REFERENCES practice_holds(code), percentile real NOT NULL CHECK(percentile BETWEEN 0 AND 1),
 neighbors int NOT NULL CHECK(neighbors>=2), replay_window jsonb NOT NULL, backtest jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS adjustment_vouchers (
 hold text PRIMARY KEY REFERENCES practice_holds(code), from_block smallint NOT NULL,to_block smallint NOT NULL,
 moved_to text NOT NULL REFERENCES rehearsal_venues(code), estimate_cents int NOT NULL CHECK(estimate_cents>=0),
 memo text NOT NULL, reviewed_by text NOT NULL, settled_by text, settled_at timestamptz,
 CHECK(0<=from_block AND from_block<to_block AND to_block<=48)
);
-- Ticket-time weather basis is immutable after issue.  The aliases keep the
-- archive readable regardless of the vocabulary used by older clients.
ALTER TABLE adjustment_vouchers ADD COLUMN IF NOT EXISTS weather_basis jsonb;
ALTER TABLE adjustment_vouchers ADD COLUMN IF NOT EXISTS weather_snapshot jsonb;
ALTER TABLE adjustment_vouchers ADD COLUMN IF NOT EXISTS weather_evidence jsonb;
ALTER TABLE adjustment_vouchers ADD COLUMN IF NOT EXISTS basis jsonb;

CREATE TABLE IF NOT EXISTS correction_batches (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 batch_key text UNIQUE,
 job_id bigint,
 status text NOT NULL DEFAULT 'queued'
   CHECK(status IN ('queued','running','failed','published','cancelled')),
 correction_from date,
 corrections jsonb NOT NULL,
 target_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
 result jsonb,
 error text,
 created_by text,
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 published_at timestamptz
);
CREATE INDEX IF NOT EXISTS correction_batches_status_from
 ON correction_batches(status, correction_from, id);

CREATE TABLE IF NOT EXISTS weather_corrections (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 batch_id bigint NOT NULL REFERENCES correction_batches(id) ON DELETE CASCADE,
 batch_key text,
 on_day date NOT NULL,
 half_from smallint NOT NULL CHECK(half_from BETWEEN 0 AND 47),
 temp_c real NOT NULL CHECK(temp_c BETWEEN -15 AND 55),
 humidity int NOT NULL CHECK(humidity BETWEEN 0 AND 100),
 source text NOT NULL,
 status text NOT NULL DEFAULT 'queued'
   CHECK(status IN ('queued','applied','failed','cancelled')),
 created_at timestamptz NOT NULL DEFAULT now(),
 applied_at timestamptz,
 UNIQUE(batch_id,on_day,half_from)
);
CREATE INDEX IF NOT EXISTS weather_corrections_day ON weather_corrections(on_day,half_from);

-- A publication row is the idempotency boundary for a successful original batch.
CREATE TABLE IF NOT EXISTS correction_publications (
 batch_id bigint PRIMARY KEY REFERENCES correction_batches(id),
 batch_key text UNIQUE,
 job_id bigint,
 target_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
 created_at timestamptz NOT NULL DEFAULT now()
);

-- Compatibility names for code/tests that use the longer domain vocabulary.
CREATE OR REPLACE VIEW weather_correction_batches AS SELECT * FROM correction_batches;
CREATE OR REPLACE VIEW weather_batches AS SELECT * FROM correction_batches;
CREATE OR REPLACE VIEW weather_revision_batches AS SELECT * FROM correction_batches;
CREATE OR REPLACE VIEW recomputation_batches AS SELECT * FROM correction_batches;
CREATE OR REPLACE VIEW correction_batch_items AS SELECT * FROM weather_corrections;
CREATE OR REPLACE VIEW correction_items AS SELECT * FROM weather_corrections;
