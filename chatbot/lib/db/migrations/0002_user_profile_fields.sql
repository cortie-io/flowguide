ALTER TABLE "User"
  ADD COLUMN IF NOT EXISTS "company" text,
  ADD COLUMN IF NOT EXISTS "jobTitle" text,
  ADD COLUMN IF NOT EXISTS "phone" varchar(30),
  ADD COLUMN IF NOT EXISTS "useCase" text;
