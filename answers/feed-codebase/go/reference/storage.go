package feed

import (
	"fmt"
	"sort"
)

// store holds everything one feed region knows, in memory.
type store struct {
	users     map[string]bool
	posts     map[string]*Post
	byAuthor  map[string][]*Post // each author's posts, oldest first (CreatedAt, then ID)
	following map[string]map[string]bool
	mutes     map[string]map[string]mute
	likes     map[[2]string]bool
}

func newStore() *store {
	return &store{
		users:     map[string]bool{},
		posts:     map[string]*Post{},
		byAuthor:  map[string][]*Post{},
		following: map[string]map[string]bool{},
		mutes:     map[string]map[string]mute{},
		likes:     map[[2]string]bool{},
	}
}

func (st *store) requireUser(id string) error {
	if !st.users[id] {
		return fmt.Errorf("%w: %s", ErrUnknownUser, id)
	}
	return nil
}

func (st *store) addPost(p Post) error {
	if _, dup := st.posts[p.ID]; dup {
		return fmt.Errorf("%w: %s", ErrDuplicatePost, p.ID)
	}
	np := &p
	st.posts[p.ID] = np
	list := st.byAuthor[p.Author]
	i := sort.Search(len(list), func(i int) bool {
		if list[i].CreatedAt != p.CreatedAt {
			return list[i].CreatedAt > p.CreatedAt
		}
		return list[i].ID > p.ID
	})
	list = append(list, nil)
	copy(list[i+1:], list[i:])
	list[i] = np
	st.byAuthor[p.Author] = list
	return nil
}

func (st *store) getPost(id string) (*Post, error) {
	p, ok := st.posts[id]
	if !ok {
		return nil, fmt.Errorf("%w: %s", ErrUnknownPost, id)
	}
	return p, nil
}

// postsBy returns the author's posts with start <= CreatedAt <= end, oldest first.
func (st *store) postsBy(author string, start, end int64) []*Post {
	posts := st.byAuthor[author]
	lo := sort.Search(len(posts), func(i int) bool { return posts[i].CreatedAt >= start })
	hi := sort.Search(len(posts), func(i int) bool { return posts[i].CreatedAt > end })
	return posts[lo:hi]
}

// addLike records userID liking postID; false if it was already recorded.
func (st *store) addLike(postID, userID string) (bool, error) {
	p, err := st.getPost(postID)
	if err != nil {
		return false, err
	}
	k := [2]string{postID, userID}
	if st.likes[k] {
		return false, nil
	}
	st.likes[k] = true
	p.Likes++
	return true, nil
}

func (st *store) follow(follower, followee string) {
	if st.following[follower] == nil {
		st.following[follower] = map[string]bool{}
	}
	st.following[follower][followee] = true
}

func (st *store) unfollow(follower, followee string) {
	delete(st.following[follower], followee)
}

// followed returns a copy of who the user follows.
func (st *store) followed(id string) map[string]bool {
	out := map[string]bool{}
	for f := range st.following[id] {
		out[f] = true
	}
	return out
}

// setMute stores a mute, replacing any earlier mute of the same account.
func (st *store) setMute(viewer string, m mute) {
	if st.mutes[viewer] == nil {
		st.mutes[viewer] = map[string]mute{}
	}
	st.mutes[viewer][m.target] = m
}

func (st *store) mutesOf(viewer string) []mute {
	var out []mute
	for _, m := range st.mutes[viewer] {
		out = append(out, m)
	}
	return out
}
