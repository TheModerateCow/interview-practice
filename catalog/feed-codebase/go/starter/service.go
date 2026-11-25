package feed

import "sort"

// CatchUpPerAuthor is the most posts one account may contribute to a catch-up list.
const CatchUpPerAuthor = 2

type rankedPost struct {
	score float64
	post  *Post
}

// Service is the home feed for one region. Times are whole seconds since the epoch.
type Service struct {
	store *store
}

// New returns an empty service.
func New() *Service { return &Service{store: newStore()} }

// accounts -------------------------------------------------------------

func (s *Service) AddUser(id string) { s.store.users[id] = true }

func (s *Service) Follow(follower, followee string) error {
	if err := s.store.requireUser(follower); err != nil {
		return err
	}
	if err := s.store.requireUser(followee); err != nil {
		return err
	}
	if follower == followee {
		return ErrSelfFollow
	}
	s.store.follow(follower, followee)
	return nil
}

func (s *Service) Unfollow(follower, followee string) error {
	if err := s.store.requireUser(follower); err != nil {
		return err
	}
	s.store.unfollow(follower, followee)
	return nil
}

// Mute hides target's posts from viewer for good.
func (s *Service) Mute(viewer, target string, now int64) error {
	return s.setMute(viewer, foreverMute(target), target)
}

// MuteFor hides target's posts from viewer from now until hours hours later.
// Muting again replaces the earlier mute.
func (s *Service) MuteFor(viewer, target string, now int64, hours float64) error {
	return s.setMute(viewer, startMute(target, now, hours), target)
}

func (s *Service) setMute(viewer string, m mute, target string) error {
	if err := s.store.requireUser(viewer); err != nil {
		return err
	}
	if err := s.store.requireUser(target); err != nil {
		return err
	}
	s.store.setMute(viewer, m)
	return nil
}

// posts ----------------------------------------------------------------

func (s *Service) Publish(id, author string, createdAt int64, text string) (Post, error) {
	if err := s.store.requireUser(author); err != nil {
		return Post{}, err
	}
	p := Post{ID: id, Author: author, CreatedAt: createdAt, Text: text}
	if err := s.store.addPost(p); err != nil {
		return Post{}, err
	}
	return p, nil
}

// Post returns a copy of the post.
func (s *Service) Post(id string) (Post, error) {
	p, err := s.store.getPost(id)
	if err != nil {
		return Post{}, err
	}
	return *p, nil
}

// Like records a like (idempotent per user) and returns the post's like count.
func (s *Service) Like(postID, userID string) (int, error) {
	if err := s.store.requireUser(userID); err != nil {
		return 0, err
	}
	if _, err := s.store.addLike(postID, userID); err != nil {
		return 0, err
	}
	p, _ := s.store.getPost(postID)
	return p.Likes, nil
}

// feeds ----------------------------------------------------------------

// HomeFeed is one page of the viewer's ranked home feed. cursor "" starts at
// the top. See problem.md for the rules.
func (s *Service) HomeFeed(viewer string, now int64, limit int, cursor string) (Page, error) {
	if limit < 1 {
		return Page{}, ErrBadLimit
	}
	if err := s.store.requireUser(viewer); err != nil {
		return Page{}, err
	}
	authors := s.sources(viewer, now)
	authors[viewer] = true
	ranked := s.ranked(authors, now-FeedWindow, now)
	if cursor != "" {
		cs, cid, err := decodeCursor(cursor)
		if err != nil {
			return Page{}, err
		}
		i := sort.Search(len(ranked), func(i int) bool {
			return ranksBefore(cs, cid, ranked[i].score, ranked[i].post.ID)
		})
		ranked = ranked[i:]
	}
	page := ranked
	if len(page) > limit {
		page = page[:limit]
	}
	out := Page{PostIDs: []string{}}
	for _, r := range page {
		out.PostIDs = append(out.PostIDs, r.post.ID)
	}
	if len(ranked) > limit {
		last := page[len(page)-1]
		out.NextCursor = encodeCursor(last.score, last.post.ID)
	}
	return out, nil
}

// CatchUp is the "while you were away" list. See problem.md for the rules.
func (s *Service) CatchUp(viewer string, since, now int64, limit int) ([]string, error) {
	panic("not implemented")
}

// internals ------------------------------------------------------------

// sources is the accounts the viewer follows, minus those muted at now.
func (s *Service) sources(viewer string, now int64) map[string]bool {
	out := s.store.followed(viewer)
	for _, m := range s.store.mutesOf(viewer) {
		if m.active(now) {
			delete(out, m.target)
		}
	}
	return out
}

// ranked is the posts by these authors published in [start, end], in feed order.
func (s *Service) ranked(authors map[string]bool, start, end int64) []rankedPost {
	var out []rankedPost
	for a := range authors {
		for _, p := range s.store.postsBy(a, start, end) {
			out = append(out, rankedPost{hotScore(p.Likes, p.CreatedAt), p})
		}
	}
	sort.Slice(out, func(i, j int) bool {
		return ranksBefore(out[i].score, out[i].post.ID, out[j].score, out[j].post.ID)
	})
	return out
}
