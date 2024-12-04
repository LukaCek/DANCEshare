const CHUNK_SIZE = 1.5 * 1024 * 1024; // 1.5MB to account for overhead

document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const file = document.getElementById('video').files[0];
    const name = document.getElementById('name').value;
    const description = document.getElementById('description').value;
    const group = document.getElementById('group').value;
    
    if (!file) {
        alert('Please select a file');
        return;
    }

    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    document.getElementById('progress').style.display = 'block';
    document.getElementById('status').textContent = 'Starting upload...';

    try {
        for (let chunkNumber = 0; chunkNumber < totalChunks; chunkNumber++) {
            const start = chunkNumber * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, file.size);
            const chunk = file.slice(start, end);

            const formData = new FormData();
            formData.append('file', chunk, 'chunk');
            formData.append('chunk_number', chunkNumber.toString());
            formData.append('total_chunks', totalChunks.toString());
            formData.append('video_name', name);
            formData.append('description', description);
            formData.append('file_type', file.type);
            formData.append('group', group);

            console.log('Sending chunk', chunkNumber, 'of', totalChunks);

            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Upload failed: ${errorText}`);
            }

            const result = await response.json();
            console.log('Chunk response:', result);

            const progress = ((chunkNumber + 1) / totalChunks) * 100;
            document.getElementById('progress-bar').style.width = progress + '%';
            document.getElementById('status').textContent = `Uploading: ${Math.round(progress)}%`;
        }
        
        document.getElementById('status').textContent = 'Upload complete!';
    } catch (error) {
        console.error('Upload error:', error);
        document.getElementById('status').textContent = 'Upload failed: ' + error.message;
    }
});