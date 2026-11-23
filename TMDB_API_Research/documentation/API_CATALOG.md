# TMDB API Catalog

Comprehensive registry of researched TMDB API v3 endpoints covering Movies, TV Shows, People, Search, Discovery, Trending, and Reference taxonomies.

| Category | Endpoint Name | Method | URL Pattern | Required Params | Optional Params | Interactive Mockup | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Movies | Movie Details | GET | `/movie/{movie_id}` | `movie_id` | `language`, `append_to_response` | `movies/movie_details.html` | Verified |
| Movies | Movie Credits | GET | `/movie/{movie_id}/credits` | `movie_id` | `language` | `movies/movie_credits.html` | Verified |
| Movies | Movie Lists (Popular) | GET | `/movie/popular` | None | `language`, `page`, `region` | `movies/movie_lists.html` | Verified |
| Movies | Movie Lists (Now Playing) | GET | `/movie/now_playing` | None | `language`, `page`, `region` | `movies/movie_lists.html` | Verified |
| Movies | Movie Lists (Top Rated) | GET | `/movie/top_rated` | None | `language`, `page`, `region` | `movies/movie_lists.html` | Verified |
| Movies | Movie Lists (Upcoming) | GET | `/movie/upcoming` | None | `language`, `page`, `region` | `movies/movie_lists.html` | Verified |
| Movies | Movie Images | GET | `/movie/{movie_id}/images` | `movie_id` | `include_image_language`, `language` | `movies/movie_images_videos.html` | Verified |
| Movies | Movie Videos | GET | `/movie/{movie_id}/videos` | `movie_id` | `language`, `include_video_language` | `movies/movie_images_videos.html` | Verified |
| Movies | Movie Recommendations | GET | `/movie/{movie_id}/recommendations` | `movie_id` | `language`, `page` | `movies/movie_recommendations_similar.html` | Verified |
| Movies | Movie Similar Titles | GET | `/movie/{movie_id}/similar` | `movie_id` | `language`, `page` | `movies/movie_recommendations_similar.html` | Verified |
| Movies | Movie Release Dates | GET | `/movie/{movie_id}/release_dates` | `movie_id` | None | `movies/movie_release_keywords.html` | Verified |
| Movies | Movie Keywords | GET | `/movie/{movie_id}/keywords` | `movie_id` | None | `movies/movie_release_keywords.html` | Verified |
| Movies | Movie External IDs | GET | `/movie/{movie_id}/external_ids` | `movie_id` | None | `movies/movie_release_keywords.html` | Verified |
| Movies | Movie Watch Providers | GET | `/movie/{movie_id}/watch/providers` | `movie_id` | None | `reference/watch_providers.html` | Verified |
| TV Shows | TV Show Details | GET | `/tv/{series_id}` | `series_id` | `language`, `append_to_response` | `tv_shows/tv_details.html` | Verified |
| TV Shows | TV Season Details | GET | `/tv/{series_id}/season/{season_number}` | `series_id`, `season_number` | `language`, `append_to_response` | `tv_shows/tv_seasons_episodes.html` | Verified |
| TV Shows | TV Episode Details | GET | `/tv/{series_id}/season/{season_number}/episode/{episode_number}` | `series_id`, `season_number`, `episode_number` | `language`, `append_to_response` | `tv_shows/tv_seasons_episodes.html` | Verified |
| TV Shows | TV Aggregate Credits | GET | `/tv/{series_id}/aggregate_credits` | `series_id` | `language` | `tv_shows/tv_credits.html` | Verified |
| TV Shows | TV Credits | GET | `/tv/{series_id}/credits` | `series_id` | `language` | `tv_shows/tv_credits.html` | Verified |
| TV Shows | TV Lists (Airing Today) | GET | `/tv/airing_today` | None | `language`, `page`, `timezone` | `tv_shows/tv_lists.html` | Verified |
| TV Shows | TV Lists (On The Air) | GET | `/tv/on_the_air` | None | `language`, `page`, `timezone` | `tv_shows/tv_lists.html` | Verified |
| TV Shows | TV Lists (Popular) | GET | `/tv/popular` | None | `language`, `page` | `tv_shows/tv_lists.html` | Verified |
| TV Shows | TV Lists (Top Rated) | GET | `/tv/top_rated` | None | `language`, `page` | `tv_shows/tv_lists.html` | Verified |
| TV Shows | TV Images | GET | `/tv/{series_id}/images` | `series_id` | `include_image_language`, `language` | `tv_shows/tv_images_videos.html` | Verified |
| TV Shows | TV Videos | GET | `/tv/{series_id}/videos` | `series_id` | `language`, `include_video_language` | `tv_shows/tv_images_videos.html` | Verified |
| TV Shows | TV Content Ratings | GET | `/tv/{series_id}/content_ratings` | `series_id` | None | `tv_shows/tv_ratings_keywords.html` | Verified |
| TV Shows | TV Keywords | GET | `/tv/{series_id}/keywords` | `series_id` | None | `tv_shows/tv_ratings_keywords.html` | Verified |
| TV Shows | TV External IDs | GET | `/tv/{series_id}/external_ids` | `series_id` | None | `tv_shows/tv_ratings_keywords.html` | Verified |
| TV Shows | TV Watch Providers | GET | `/tv/{series_id}/watch/providers` | `series_id` | None | `reference/watch_providers.html` | Verified |
| People | Person Details | GET | `/person/{person_id}` | `person_id` | `language`, `append_to_response` | `people/person_details.html` | Verified |
| People | Person Combined Credits | GET | `/person/{person_id}/combined_credits` | `person_id` | `language` | `people/person_credits.html` | Verified |
| People | Person Movie Credits | GET | `/person/{person_id}/movie_credits` | `person_id` | `language` | `people/person_credits.html` | Verified |
| People | Person TV Credits | GET | `/person/{person_id}/tv_credits` | `person_id` | `language` | `people/person_credits.html` | Verified |
| People | Person Images | GET | `/person/{person_id}/images` | `person_id` | None | `people/person_details.html` | Verified |
| People | Popular People | GET | `/person/popular` | None | `language`, `page` | `people/person_popular.html` | Verified |
| Search | Multi Search | GET | `/search/multi` | `query` | `include_adult`, `language`, `page` | `search/search_multi.html` | Verified |
| Search | Movie Search | GET | `/search/movie` | `query` | `include_adult`, `language`, `primary_release_year`, `page`, `region`, `year` | `search/search_movies.html` | Verified |
| Search | TV Search | GET | `/search/tv` | `query` | `first_air_date_year`, `include_adult`, `language`, `page`, `year` | `search/search_tv.html` | Verified |
| Search | Person Search | GET | `/search/person` | `query` | `include_adult`, `language`, `page` | `people/person_popular.html` | Verified |
| Discover | Discover Movies | GET | `/discover/movie` | None | `sort_by`, `with_genres`, `vote_count.gte`, `vote_average.gte`, `primary_release_year`, `page` | `discover/discover_movies.html` | Verified |
| Discover | Discover TV | GET | `/discover/tv` | None | `sort_by`, `with_genres`, `first_air_date_year`, `with_networks`, `page` | `discover/discover_tv.html` | Verified |
| Trending | Trending All | GET | `/trending/all/{time_window}` | `time_window` (`day`, `week`) | `language` | `trending/trending.html` | Verified |
| Trending | Trending Movies | GET | `/trending/movie/{time_window}` | `time_window` (`day`, `week`) | `language` | `trending/trending.html` | Verified |
| Trending | Trending TV | GET | `/trending/tv/{time_window}` | `time_window` (`day`, `week`) | `language` | `trending/trending.html` | Verified |
| Trending | Trending People | GET | `/trending/person/{time_window}` | `time_window` (`day`, `week`) | `language` | `trending/trending.html` | Verified |
| Taxonomy | Movie Genres | GET | `/genre/movie/list` | None | `language` | `reference/genres_certifications.html` | Verified |
| Taxonomy | TV Genres | GET | `/genre/tv/list` | None | `language` | `reference/genres_certifications.html` | Verified |
| Taxonomy | Movie Certifications | GET | `/certification/movie/list` | None | None | `reference/genres_certifications.html` | Verified |
| Taxonomy | TV Certifications | GET | `/certification/tv/list` | None | None | `reference/genres_certifications.html` | Verified |
| Providers | Watch Providers (Movie) | GET | `/watch/providers/movie` | None | `language`, `watch_region` | `reference/watch_providers.html` | Verified |
| Providers | Watch Providers (TV) | GET | `/watch/providers/tv` | None | `language`, `watch_region` | `reference/watch_providers.html` | Verified |
| Franchise | Collection Details | GET | `/collection/{collection_id}` | `collection_id` | `language` | `reference/collections.html` | Verified |
| System | System Configuration | GET | `/configuration` | None | None | `reference/configuration.html` | Verified |
