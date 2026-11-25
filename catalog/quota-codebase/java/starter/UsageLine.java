/**
 * One key's row in an organisation's usage report.
 *
 * @param requests allowed requests
 * @param units    units spent by allowed requests
 * @param denied   requests the limiter rejected
 */
public record UsageLine(String keyId, String plan, long requests, long units, long denied) {}
