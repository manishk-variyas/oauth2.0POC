

import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom';
import { BookOpen, Home } from 'lucide-react';
import { fetchPublicNotes } from '../services/notes';
import './Public.css';

function Public() {
    const [publicNotes,setPublicNotes] = useState([])
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadPublicNotes = async () => {
            try {
                const notes = await fetchPublicNotes();
                setPublicNotes(notes);
            } catch (error) {
                console.error('Failed to load public notes:', error);
            } finally {
                setLoading(false);
            }
        };
        loadPublicNotes();
    },[])
  return (
    <div className="public-container">
      <header className="public-header">
        <div className="header-left">
          <BookOpen className="logo-icon" />
          <h1>Public Notes</h1>
        </div>
        <Link to="/" className="home-link">
            <Home size={18} />
            Home
        </Link>
      </header>

      <main className="public-content">
        <h2>Community Notes</h2>

        {loading ? (
          <div className="loading">Loading...</div>
        ) : publicNotes.length === 0 ? (
          <div className="empty-state">
            <BookOpen size={48} />
            <p>No public notes available yet.</p>
          </div>
        ) : (
          <div className="notes-grid">
            {publicNotes.map(note => (
                <div key={note.id} className="note-card">
                    <div className="note-header">
                        <h3>{note.title}</h3>
                        <span className="author-badge">{note.author || 'Anonymous'}</span>
                    </div>
                    <p className="note-content">{note.content}</p>
                    <div className="note-footer">
                        <span className="note-date">
                            {new Date(note.created_at).toLocaleDateString()}
                        </span>
                    </div>
                </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

export default Public