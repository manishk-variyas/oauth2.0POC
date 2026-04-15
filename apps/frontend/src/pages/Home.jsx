import { useState, useEffect } from 'react';
import { Plus, Trash2, LogOut, User, BookOpen, Globe } from 'lucide-react';
import { Link } from 'react-router-dom';
import { getNotes, createNote, deleteNote } from '../services/notes';
import { useAuth } from '../App';
import './Home.css';

function Home() {
  const { user, logout } = useAuth();
  const [notes, setNotes] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [newNote, setNewNote] = useState({ title: '', content: '', is_public: false });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadNotes();
  }, []);

  const loadNotes = async () => {
    try {
      const data = await getNotes();
      setNotes(data);
    } catch (error) {
      console.error('Failed to load notes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNote = async (e) => {
    e.preventDefault();
    try {
      await createNote(newNote);
      setNewNote({ title: '', content: '', is_public: false });
      setShowForm(false);
      loadNotes();
    } catch (error) {
      console.error('Failed to create note:', error);
    }
  };

  const openForm = () => {
    setNewNote({ title: '', content: '', is_public: false });
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setNewNote({ title: '', content: '', is_public: false });
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this note?')) return;
    try {
      await deleteNote(id);
      loadNotes();
    } catch (error) {
      console.error('Failed to delete note:', error);
    }
  };

  return (
    <div className="home-container">
      <header className="header">
        <div className="header-left">
          <BookOpen className="logo-icon" />
          <h1>Notes</h1>
        </div>
        <div className="header-right">
          <Link to="/public" className="public-link">
            <Globe size={18} />
            Public
          </Link>
          <div className="user-info">
            <User size={18} />
            <span>{user?.username || 'User'}</span>
          </div>
          <button onClick={logout} className="logout-btn">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <main className="main-content">
        <div className="notes-header">
          <h2>Your Notes</h2>
          <button onClick={openForm} className="add-btn">
            <Plus size={20} />
            Add Note
          </button>
        </div>

        {showForm && (
          <div className="modal-overlay" onClick={closeForm}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Create New Note</h2>
                <button className="close-btn" onClick={closeForm}>&times;</button>
              </div>
              <form onSubmit={handleCreateNote}>
                <input
                  type="text"
                  placeholder="Title"
                  value={newNote.title}
                  onChange={(e) => setNewNote({ ...newNote, title: e.target.value })}
                  required
                  className="modal-input"
                />
                <textarea
                  placeholder="Write your note here..."
                  value={newNote.content}
                  onChange={(e) => setNewNote({ ...newNote, content: e.target.value })}
                  rows={6}
                  className="modal-textarea"
                />
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={newNote.is_public}
                    onChange={(e) => setNewNote({ ...newNote, is_public: e.target.checked })}
                  />
                  Make this note public
                </label>
                <div className="form-actions">
                  <button type="submit" className="save-btn">Create Note</button>
                  <button type="button" onClick={closeForm} className="cancel-btn">
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {loading ? (
          <div className="loading">Loading...</div>
        ) : notes.length === 0 ? (
          <div className="empty-state">
            <BookOpen size={48} />
            <p>No notes yet. Create your first note!</p>
          </div>
        ) : (
          <div className="notes-grid">
            {notes.map((note) => (
              <div key={note.id} className="note-card">
                <div className="note-header">
                  <h3>{note.title}</h3>
                  {note.is_public && <span className="public-badge">Public</span>}
                </div>
                <p className="note-content">{note.content || 'No content'}</p>
                <div className="note-footer">
                  <span className="note-date">
                    {new Date(note.created_at).toLocaleDateString()}
                  </span>
                  {note.user_id === user?.sub && (
                    <button onClick={() => handleDelete(note.id)} className="delete-btn">
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

export default Home;