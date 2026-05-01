import http from './http'

export const tmdbApi = {
  discover(params) {
    return http.get('/tmdb/discover', { params })
  },
  getGenres(media_type) {
    return http.get(`/tmdb/genres/${media_type}`)
  },
  getFullDetails(media_type, tmdb_id) {
    return http.get(`/tmdb/detail/${media_type}/${tmdb_id}`)
  }
}
