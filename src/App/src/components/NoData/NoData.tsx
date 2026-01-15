import { useTranslation } from "react-i18next";

const NoData = () => {
  const { t } = useTranslation();
  return (
    <div className="no-data-container">
      <span style={{"fontWeight":"bold"}}>{t("message.noDataAvailable")}</span>
    </div>
  );
};

export default NoData;
