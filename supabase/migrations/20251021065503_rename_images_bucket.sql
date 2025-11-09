-- Drop existing policies for collectible-images bucket
DROP POLICY IF EXISTS "Public read access for collectible images" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can upload collectible images" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can update collectible images" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can delete collectible images" ON storage.objects;

-- Delete old bucket
DELETE FROM storage.buckets WHERE id = 'collectible-images';

-- Create new bucket with simpler name
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'images',
  'images',
  true,  -- Public bucket (no auth required for reads)
  5242880,  -- 5MB file size limit
  ARRAY['image/jpeg', 'image/png', 'image/gif', 'image/webp']  -- Allowed image types
)
ON CONFLICT (id) DO NOTHING;

-- Create storage policy for public read access
CREATE POLICY "Public read access for images"
ON storage.objects
FOR SELECT
USING (bucket_id = 'images');

-- Create storage policy for authenticated users to upload
CREATE POLICY "Authenticated users can upload images"
ON storage.objects
FOR INSERT
WITH CHECK (
  bucket_id = 'images'
  AND auth.role() = 'authenticated'
);

-- Create storage policy for authenticated users to update their uploads
CREATE POLICY "Authenticated users can update images"
ON storage.objects
FOR UPDATE
USING (bucket_id = 'images' AND auth.role() = 'authenticated')
WITH CHECK (bucket_id = 'images' AND auth.role() = 'authenticated');

-- Create storage policy for authenticated users to delete their uploads
CREATE POLICY "Authenticated users can delete images"
ON storage.objects
FOR DELETE
USING (bucket_id = 'images' AND auth.role() = 'authenticated');
