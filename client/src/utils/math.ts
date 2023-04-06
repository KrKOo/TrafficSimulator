import { LatLng } from 'types/roadnet';

const degToRad = (deg: number) => {
  return deg * (Math.PI / 180);
};

const coordsToRad = (coords: LatLng) => {
  return {
    lat: degToRad(coords.lat),
    lng: degToRad(coords.lng),
  };
};

export const haversine = (coord1: LatLng, coord2: LatLng) => {
  const R = 6371; // km

  coord1 = coordsToRad(coord1);
  coord2 = coordsToRad(coord2);

  const dLat = coord2.lat - coord1.lat;
  const dLon = coord2.lng - coord1.lng;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(coord1.lat) *
      Math.cos(coord2.lat) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.asin(Math.sqrt(a));
  const d = R * c;

  return d;
};
