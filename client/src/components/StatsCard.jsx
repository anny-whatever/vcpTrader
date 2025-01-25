import { Card, CardHeader, CardBody, Image } from "@heroui/react";

export default function StatsCard({}) {
  return (
    <Card className="py-4 m-5 w-fit">
      <CardHeader className="flex-col items-start px-4 pt-2 pb-0">
        <p className="font-bold uppercase text-tiny">Daily Mix</p>
        <small className="text-default-500">12 Tracks</small>
        <h4 className="font-bold text-large">Frontend Radio</h4>
      </CardHeader>
      <CardBody className="py-2 overflow-visible">
        <Image
          alt="Card background"
          className="object-cover rounded-xl"
          src="https://nextui.org/images/hero-card-complete.jpeg"
          width={270}
        />
      </CardBody>
    </Card>
  );
}
