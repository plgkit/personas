/** A problem in the call, the config, or the database. */
export class PlgkitError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PlgkitError";
  }
}
