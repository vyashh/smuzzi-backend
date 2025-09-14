package main

import (
	"log"
	"net/http"
	"smuzzi/backend/handlers"
)

func main() {
	http.HandleFunc("/api/stream", handlers.StreamSong)

	log.Println("🎵 Smuzzi backend running at http://localhost:3000")
	log.Fatal(http.ListenAndServe(":3000", nil))
}
