// Fuente única de datos de las personas de la historia de la lógica.
// Solo datos y ayudas puras. Los retratos son copias locales (ver img/CREDITOS.md);
// si `image` es null la interfaz muestra las iniciales. Si la licencia es CC BY / CC BY-SA,
// el crédito debe mostrarse visible junto al retrato.
export const PEOPLE = {
  aristoteles: {name: 'Aristóteles', born: -384, died: -322, image: '/img/people/aristoteles.jpg', credit: 'Copia romana de Lisipo (foto: Jastrow, 2006) · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:Aristotle_Altemps_Inv8575.jpg', license: 'Dominio público'},
  leibniz: {name: 'Gottfried Wilhelm Leibniz', born: 1646, died: 1716, image: '/img/people/leibniz.jpg', credit: 'Christoph Bernhard Francke · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:Christoph_Bernhard_Francke_-_Bildnis_des_Philosophen_Leibniz_(ca._1695)_(cropped)2.jpg', license: 'Dominio público'},
  boole: {name: 'George Boole', born: 1815, died: 1864, image: '/img/people/boole.jpg', credit: 'Autor desconocido (National Portrait Gallery, Londres) · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:George_Boole_by_unknown_artist_1847.jpg', license: 'Dominio público'},
  frege: {name: 'Gottlob Frege', born: 1848, died: 1925, image: '/img/people/frege.jpg', credit: 'Autor desconocido · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:Young_frege.jpg', license: 'Dominio público'},
  peirce: {name: 'Charles Sanders Peirce', born: 1839, died: 1914, image: '/img/people/peirce.jpg', credit: 'Napoleon Sarony · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:Charles_Sanders_Peirce.jpg', license: 'Dominio público'},
  schroder: {name: 'Ernst Schröder', born: 1841, died: 1902, image: '/img/people/schroder.jpg', credit: 'Autor no indicado · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:Ernst_schroeder.jpg', license: 'Dominio público'},
  peano: {name: 'Giuseppe Peano', born: 1858, died: 1932, image: '/img/people/peano.jpg', credit: 'Autor desconocido · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:Giuseppe_Peano.jpg', license: 'Dominio público'},
  russell: {name: 'Bertrand Russell', born: 1872, died: 1970, image: '/img/people/russell.jpg', credit: 'Bassano Ltd · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:Bertrand_Russell_in_1936.jpg', license: 'Dominio público'},
  whitehead: {name: 'Alfred North Whitehead', born: 1861, died: 1947, image: '/img/people/whitehead.jpg', credit: 'Autor desconocido · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:ANWhitehead.jpg', license: 'Dominio público'},
  lowenheim: {name: 'Leopold Löwenheim', born: 1878, died: 1957, image: '/img/people/lowenheim.jpg', credit: 'Autor desconocido (MacTutor, Univ. de St Andrews) · CC BY-SA 4.0 · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:Lowenheim_Portrait.jpg', license: 'CC BY-SA 4.0'},
  skolem: {name: 'Thoralf Skolem', born: 1887, died: 1963, image: '/img/people/skolem.jpg', credit: 'Autor desconocido (Oslo Museum) · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:ThoralfSkolem-OB.F06426c.jpg', license: 'Dominio público'},
  hilbert: {name: 'David Hilbert', born: 1862, died: 1943, image: '/img/people/hilbert.jpg', credit: 'Autor desconocido · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:Hilbert.jpg', license: 'Dominio público'},
  ackermann: {name: 'Wilhelm Ackermann', born: 1896, died: 1962, image: '/img/people/ackermann.jpg', credit: 'Autor desconocido · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:Ackermann_Wilhelm.jpg', license: 'Dominio público'},
  bernays: {name: 'Paul Bernays', born: 1888, died: 1977, image: '/img/people/bernays.jpg', credit: 'Autor desconocido (ETH-Bibliothek) · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:ETH-BIB-Bernays,_Paul_(1888-1977)-Portrait-Portr_00025_(cropped).tif', license: 'Dominio público'},
  godel: {name: 'Kurt Gödel', born: 1906, died: 1978, image: '/img/people/godel.jpg', credit: 'Autor desconocido (Institute for Advanced Study) · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:Young_Kurt_G%C3%B6del_as_a_student_in_1925.jpg', license: 'Dominio público'},
  church: {name: 'Alonzo Church', born: 1903, died: 1995, image: null, credit: '', creditUrl: '', license: ''},
  turing: {name: 'Alan Turing', born: 1912, died: 1954, image: '/img/people/turing.jpg', credit: 'Elliott & Fry · Dominio público · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:Alan_Turing_(1951).jpg', license: 'Dominio público'},
  tarski: {name: 'Alfred Tarski', born: 1901, died: 1983, image: '/img/people/tarski.jpg', credit: 'George Bergman (Oberwolfach Photo Collection) · CC BY-SA 4.0 · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:Alfred_Tarski_1968_(as-is,_cropped).jpg', license: 'CC BY-SA 4.0'},
  gentzen: {name: 'Gerhard Gentzen', born: 1909, died: 1945, image: '/img/people/gentzen.jpg', credit: 'Eckart Menzler-Trott (Oberwolfach Photo Collection) · CC BY-SA 2.0 DE · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:Gerhard_Gentzen.jpg', license: 'CC BY-SA 2.0 DE'},
  jaskowski: {name: 'Stanisław Jaśkowski', born: 1906, died: 1965, image: null, credit: '', creditUrl: '', license: ''},
  fitch: {name: 'Frederic Fitch', born: 1908, died: 1987, image: null, credit: '', creditUrl: '', license: ''},
  robinson: {name: 'John Alan Robinson', born: 1930, died: 2016, image: '/img/people/robinson.jpg', credit: 'David Monniaux · CC BY-SA 3.0 · Wikimedia Commons', creditUrl: 'https://commons.wikimedia.org/wiki/File:John_Alan_Robinson_IMG_0493.jpg', license: 'CC BY-SA 3.0'},
};

export const PEOPLE_ORDER = Object.keys(PEOPLE);

export function person(slug) {
  return Object.prototype.hasOwnProperty.call(PEOPLE, slug) ? {slug, ...PEOPLE[slug]} : null;
}

export function initials(slug) {
  const p = PEOPLE[slug];
  if (!p) return '';
  const w = p.name.split(/\s+/).filter(Boolean);
  return (w.length > 1 ? w[0][0] + w[w.length - 1][0] : w[0].slice(0, 2)).toUpperCase();
}

// «384 a. C. – 322 a. C.», «1906 – 1978»; un año desconocido (null) se omite.
export function lifespan(slug) {
  const p = PEOPLE[slug];
  if (!p) return '';
  const y = (v) => (v == null ? '?' : v < 0 ? `${-v} a. C.` : String(v));
  return `${y(p.born)} – ${y(p.died)}`;
}
