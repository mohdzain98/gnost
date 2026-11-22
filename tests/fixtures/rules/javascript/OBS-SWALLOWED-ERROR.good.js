function save(data) {
  try {
    write(data);
  } catch (err) {
    console.error('save failed', err);
  }
  try {
    write(data);
  } catch (err) {
    throw new Error('save failed', { cause: err });
  }
  try {
    write(data);
  } catch (err) {
    callback(err);
  }
  try {
    write(data);
  } catch {
    // the cache is optional
  }
  try {
    write(data);
  } catch {
    setSaveError(true);
  }
}
