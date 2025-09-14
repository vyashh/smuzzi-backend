package handlers

import (
	"net/http"
	"os"
	"path/filepath"
	"strconv"
)

func StreamSong(w http.ResponseWriter, r *http.Request) {
	// Example: /api/stream?song=track1.mp3
	song := r.URL.Query().Get("song")
	if song == "" {
		http.Error(w, "Missing song parameter", http.StatusBadRequest)
		return
	}

	filePath := filepath.Join("music", song)
	file, err := os.Open(filePath)
	if err != nil {
		http.Error(w, "File not found", http.StatusNotFound)
		return
	}
	defer file.Close()

	fi, _ := file.Stat()
	size := fi.Size()

	// Handle Range requests
	rangeHeader := r.Header.Get("Range")
	if rangeHeader == "" {
		w.Header().Set("Content-Length", strconv.FormatInt(size, 10))
		w.Header().Set("Content-Type", "audio/mpeg")
		http.ServeContent(w, r, song, fi.ModTime(), file)
		return
	}

	// Let http.ServeContent handle partial requests
	w.Header().Set("Content-Type", "audio/mpeg")
	http.ServeContent(w, r, song, fi.ModTime(), file)
}
