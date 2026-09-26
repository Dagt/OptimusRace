/* Preserve the simulation prefix for legacy JS requests using root-relative URLs. */
(() => {
 const prefix = document.currentScript.dataset.prefix;
 const nativeFetch = window.fetch.bind(window);
 const scoped = value => {
  const url = new URL(value, location.href);
  if (url.origin === location.origin && !/^\/(static|media|simulations)\//.test(url.pathname)) url.pathname = prefix + url.pathname;
  return url.href;
 };
 window.fetch = (input, options) => nativeFetch(input instanceof Request ? new Request(scoped(input.url), input) : scoped(input), options);
})();
