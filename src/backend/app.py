from flask import Flask, request, jsonify, send_from_directory
import os
import json
from datetime import datetime, UTC
import sys
import logging
from pathlib import Path

# Get the directory containing app.py
BACKEND_DIR = Path(__file__).resolve().parent
# Frontend directory is at src/frontend relative to the app root
FRONTEND_DIR = BACKEND_DIR.parent / 'frontend'

app = Flask(__name__, static_folder=str(FRONTEND_DIR))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_data_dir():
    """Determine the appropriate data directory based on environment"""
    try:
        if os.environ.get('FLATPAK_ID'):
            base_dir = Path(os.environ.get('XDG_DATA_HOME', 
                                         str(Path.home() / '.var' / 'app' / os.environ['FLATPAK_ID'] / 'data')))
        else:
            base_dir = Path.home() / '.local' / 'share' / 'ntepd'
        
        notes_dir = base_dir / 'notes'
        notes_dir.mkdir(parents=True, exist_ok=True)
        
        # Test write permissions
        test_file = notes_dir / '.write_test'
        test_file.touch()
        test_file.unlink()
        
        return notes_dir
    except PermissionError:
        logger.error("No permission to access or create data directory")
        raise
    except Exception as e:
        logger.error(f"Error setting up data directory: {e}")
        raise

# Set up the notes directory
NOTES_DIR = get_data_dir()
NOTES_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Using notes directory: {NOTES_DIR}")

def get_next_id():
    """Get the next available note ID"""
    existing_ids = [
        int(f.stem) for f in NOTES_DIR.glob('*.json')
        if f.stem.isdigit()
    ]
    return max(existing_ids, default=0) + 1

def load_note(filepath):
    """Load a note from a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {filepath}")
        return None
    except Exception as e:
        logger.error(f"Error reading note {filepath}: {e}")
        return None

@app.route('/')
def serve_root():
    logger.info(f"Serving root from {app.static_folder}")
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        logger.error(f"Error serving index.html: {e}")
        return str(e), 500

@app.route('/<path:path>')
def serve_static(path):
    logger.info(f"Serving static file: {path}")
    return send_from_directory(app.static_folder, path)

@app.route('/api/notes', methods=['GET'])
def get_notes():
    notes = []
    for filepath in NOTES_DIR.glob('*.json'):
        note = load_note(filepath)
        if note:
            notes.append(note)
    
    return jsonify(sorted(notes, key=lambda x: x['created_at'], reverse=True))

@app.route('/api/notes', methods=['POST'])
def create_note():
    try:
        data = request.get_json()
        note_id = get_next_id()
        note = {
            'id': note_id,
            'title': data['title'],
            'content': data['content'],
            'created_at': datetime.now(UTC).isoformat(),
            'updated_at': datetime.now(UTC).isoformat()
        }
        
        filepath = NOTES_DIR / f'{note_id}.json'
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(note, f, ensure_ascii=False, indent=2)
        
        return jsonify(note)
    except Exception as e:
        logger.error(f"Error creating note: {e}")
        return jsonify({'error': 'Failed to create note'}), 500

@app.route('/api/notes/<int:id>', methods=['PUT'])
def update_note(id):
    filepath = NOTES_DIR / f'{id}.json'
    if not filepath.exists():
        return '', 404
    
    try:
        note = load_note(filepath)
        if not note:
            return jsonify({'error': 'Failed to load note'}), 500
        
        data = request.get_json()
        note['title'] = data['title']
        note['content'] = data['content']
        note['updated_at'] = datetime.now(UTC).isoformat()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(note, f, ensure_ascii=False, indent=2)
        
        return jsonify(note)
    except Exception as e:
        logger.error(f"Error updating note {id}: {e}")
        return jsonify({'error': 'Failed to update note'}), 500

@app.route('/api/notes/<int:id>', methods=['DELETE'])
def delete_note(id):
    filepath = NOTES_DIR / f'{id}.json'
    try:
        if filepath.exists():
            filepath.unlink()
        return '', 204
    except Exception as e:
        logger.error(f"Error deleting note {id}: {e}")
        return jsonify({'error': 'Failed to delete note'}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Endpoint to check if the backend is running"""
    return jsonify({
        'status': 'running',
        'data_directory': str(NOTES_DIR),
        'note_count': len(list(NOTES_DIR.glob('*.json')))
    })

def main():
    # Check if running as Electron app
    is_electron = '--electron' in sys.argv
    
    if is_electron:
        # When running in Electron, only listen on localhost
        app.run(host='127.0.0.1', port=3547, debug=False)
    else:
        # Standard development mode
        app.run(debug=True, port=3547)

logger.info(f"Using notes directory: {NOTES_DIR}")

if __name__ == '__main__':
    main()