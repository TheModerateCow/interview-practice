package notify

import "sort"

// Digest builds the user's daily digest of held notifications: those from
// the user's local day before the one containing now. See problem.md.
func (s *Service) Digest(id string, now int64) ([]DigestLine, error) {
	u, ok := s.store.user(id)
	if !ok {
		return nil, ErrUnknownUser
	}
	to := localMidnight(now, u.OffsetMin)
	from := to - daySeconds
	out := []DigestLine{}
	idx := map[string]int{}
	for _, r := range s.store.log(id) {
		if r.Status != Held || r.At < from || r.At >= to {
			continue
		}
		i, ok := idx[r.Topic]
		if !ok {
			i = len(out)
			idx[r.Topic] = i
			out = append(out, DigestLine{Topic: r.Topic})
		}
		out[i].Count++
		out[i].Latest = r.Title
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Count != out[j].Count {
			return out[i].Count > out[j].Count
		}
		return out[i].Topic < out[j].Topic
	})
	return out, nil
}
